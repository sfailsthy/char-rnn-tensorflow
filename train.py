import codecs
import os
from utils import TextReader, batch_generator, pick_top_n
from CharRNN import CharRNN
import tensorflow as tf
import time

FLAGS = tf.flags.FLAGS

tf.flags.DEFINE_string('name', 'default', 'the name of the model')
tf.flags.DEFINE_integer('num_seqs', 100, 'number of seqs in batch')
tf.flags.DEFINE_integer('num_steps', 100, 'length of one seq')
tf.flags.DEFINE_integer('lstm_size', 128, 'size of hidden layer')
tf.flags.DEFINE_integer('num_layers', 3, 'number of lstm layers')
tf.flags.DEFINE_boolean('use_embedding', False, 'if use embedding')
tf.flags.DEFINE_integer('embedding_size', 128, 'size of embedding')
tf.flags.DEFINE_float('learning_rate', 1e-4, 'learning_rate')
tf.flags.DEFINE_float('train_keep_prob', 0.5,
                      'dropout rate during training process')
tf.flags.DEFINE_string('input_file', None, 'utf-8 encoded input file')
tf.flags.DEFINE_integer('max_steps', 100000, 'max steps of training')
tf.flags.DEFINE_integer('save_model_every', 1000,
                        'save the model every 1000 steps')
tf.flags.DEFINE_integer('log_every', 10, 'log the summaries every 10 steps')
tf.flags.DEFINE_integer('max_vocab', 3500, 'the maximum of char number')


def main(_):
    model_path = os.path.join(FLAGS.name, 'model')
    logdir_path = os.path.join(FLAGS.name, 'logdir')

    with codecs.open(FLAGS.input_file, encoding='utf-8') as f:
        text = f.read()
    Reader = TextReader(text, FLAGS.max_vocab)

    arr = Reader.text_to_arr(text)
    g = batch_generator(arr, FLAGS.num_seqs, FLAGS.num_steps)

    with tf.Session() as sess:
        char_rnn = CharRNN(
            num_classes=Reader.vocab_size,
            num_seqs=FLAGS.num_seqs,
            num_steps=FLAGS.num_steps,
            lstm_size=FLAGS.lstm_size,
            num_layers=FLAGS.num_layers,
            learning_rate=FLAGS.learning_rate,
            train_keep_prob=FLAGS.train_keep_prob,
            use_embedding=FLAGS.use_embedding,
            embedding_size=FLAGS.embedding_size)

        # define training procedure
        global_step = tf.Variable(0, trainable=False, name='global_step')
        optimizer = tf.train.AdamOptimizer(learning_rate=FLAGS.learning_rate)
        # 使用clipping gradients
        tvars = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(
            tf.gradients(ys=char_rnn.loss, xs=tvars),
            clip_norm=char_rnn.grad_clip)
        train_op = optimizer.apply_gradients(
            grads_and_vars=zip(grads, tvars), global_step=global_step)
        '''
        # Keep track of gradient values and sparsity (optional)
        print(sess.run(grads_and_vars))
        grad_summaries = []
        for g, v in grads_and_vars:
            if g is not None:
                grad_hist_summary = tf.summary.histogram(
                    '{}/grad/hist'.format(v.name), g)
                sparsity_summary = tf.summary.scalar(
                    '{}/grad/sparsity'.format(v.name), tf.nn.zero_fraction(g))
                grad_summaries.append(grad_hist_summary)
                grad_summaries.append(sparsity_summary)
        grad_summaries_merged = tf.summary.merge(grad_summaries)
        loss_summary = tf.summary.scalar('loss', char_rnn.loss)

        # Train Summaries
        train_summary_op = tf.summary.merge(
            [loss_summary, grad_summaries_merged])
        train_summary_writer = tf.summary.FileWriter(logdir_path, sess.graph)
        saver = tf.train.Saver(
            tf.global_variables(), max_to_keep=FLAGS.log_every)
        '''
        saver = tf.train.Saver()
        sess.run(tf.global_variables_initializer())
        if os.path.exists(model_path):
            sess = saver.restore(sess, model_path)
        else:
            os.makedirs(model_path)
        new_state = sess.run(char_rnn.initial_state)

        for x, y in g:
            start = time.time()
            feed_dict = {
                char_rnn.inputs: x,
                char_rnn.targets: y,
                char_rnn.keep_prob: FLAGS.train_keep_prob,
                char_rnn.initial_state: new_state
            }
            '''
            _, step, new_state, summaries, loss = sess.run([
                train_op, global_step, char_rnn.final_state, train_summary_op,
                char_rnn.loss
            ], feed_dict)
            '''
            _, step, new_state, loss = sess.run(
                [train_op, global_step, char_rnn.final_state,
                 char_rnn.loss], feed_dict)
            # train_summary_writer.add_summary(summaries, step)
            end = time.time()
            current_step = tf.train.global_step(sess, global_step)
            if step % FLAGS.log_every == 0:
                print('step: {}/{}... '.format(step, FLAGS.max_steps),
                      'loss: {:.4f}... '.format(loss),
                      '{:.4f} sec/batch'.format((end - start)))
            if current_step % FLAGS.save_model_every == 0:
                saver.save(
                    sess,
                    os.path.join(model_path, 'model'),
                    global_step=current_step)
            if current_step >= FLAGS.max_steps:
                break


if __name__ == '__main__':
    tf.app.run()