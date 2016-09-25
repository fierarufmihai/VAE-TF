
# coding: utf-8

# In[1]:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# In[2]:

# Import data
from tensorflow.examples.tutorials.mnist import input_data


# In[3]:

import tensorflow as tf
import os
from PIL import Image


# In[4]:

# Define flags

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('DATA_DIR', '/tmp/data/', 'Directory for storing data')
flags.DEFINE_string('MODEL_PATH', 'models/model.ckpt', 'Path to the parameters of the trained model')

flags.DEFINE_integer('INPUT_SIZE', 784, 'Size of the input image')
flags.DEFINE_integer('HIDDEN_ENCODER_SIZE', 400, 'Size of the hidden layer in the encoder')
flags.DEFINE_integer('HIDDEN_DECODER_SIZE', 400, 'Size of the hidden layer in the decoder')
flags.DEFINE_integer('LATENT_SPACE_SIZE', 20, 'Size of the latent space ')

flags.DEFINE_float('ADAGRAD_LR', 0.01, 'Learning rate Adagrad')   # Try with {0.01, 0.02, 0.1}
flags.DEFINE_integer('MINIBATCH_SIZE', 100, 'Size of minibatch')
flags.DEFINE_integer('NUMBER_ITERATIONS', 1000, 'Number of iterations for optimization')

flags.DEFINE_float('INIT_STD_DEV', 0.01, 'Standard deviation for the truncated normal used for initializing the weights')

flags.DEFINE_boolean('TRAIN', True, 'If False, uses saved parameters instead of training')
flags.DEFINE_boolean('TEST', True, 'If False, does not do testing')


flags.DEFINE_integer('NO_IMG_TO_SHOW', 10, 'Number of images to show in tensorboard')

# In[5]:

mnist = input_data.read_data_sets(FLAGS.DATA_DIR, one_hot=True)


# In[6]:

# Helpers

def create_W(shape):
    return tf.Variable(tf.truncated_normal(shape, stddev=FLAGS.INIT_STD_DEV))

def create_b(shape):
    return tf.Variable(tf.zeros(shape))


# In[7]:

# Define Layers

# Input
x = tf.placeholder(tf.float32, [None, FLAGS.INPUT_SIZE])

# Encoder
W_x_h_enc = create_W([FLAGS.INPUT_SIZE, FLAGS.HIDDEN_ENCODER_SIZE])
b_x_h_enc = create_b([FLAGS.HIDDEN_ENCODER_SIZE])
h_enc = tf.tanh(tf.add(tf.matmul(x, W_x_h_enc), b_x_h_enc))

W_h_mu_enc = create_W([FLAGS.HIDDEN_ENCODER_SIZE, FLAGS.LATENT_SPACE_SIZE])
b_h_mu_enc = create_b([FLAGS.LATENT_SPACE_SIZE])
mu_enc = tf.tanh(tf.add(tf.matmul(h_enc, W_h_mu_enc), b_h_mu_enc))

W_h_logsigma2_enc = create_W([FLAGS.HIDDEN_ENCODER_SIZE, FLAGS.LATENT_SPACE_SIZE])
b_h_logsigma2_enc = create_b([FLAGS.LATENT_SPACE_SIZE])
logsigma2_enc = tf.tanh(tf.add(tf.matmul(h_enc, W_h_logsigma2_enc), b_h_logsigma2_enc))

# Sampler
eps_enc = tf.random_normal(shape=tf.shape(mu_enc))
sigma_enc = tf.exp(0.5 * logsigma2_enc)
z = tf.add(tf.mul(sigma_enc, eps_enc), mu_enc)

# Decoder
W_z_h_dec = create_W([FLAGS.LATENT_SPACE_SIZE, FLAGS.HIDDEN_DECODER_SIZE])
b_z_h_dec = create_b([FLAGS.HIDDEN_DECODER_SIZE])
h_dec = tf.tanh(tf.add(tf.matmul(z, W_z_h_dec), b_z_h_dec))

W_h_x_dec = create_W([FLAGS.HIDDEN_DECODER_SIZE, FLAGS.INPUT_SIZE])
b_h_x_dec = create_b([FLAGS.INPUT_SIZE])
x_dec = tf.add(tf.matmul(h_dec, W_h_x_dec), b_h_x_dec)

log_p_x_z = tf.reduce_sum(-tf.nn.sigmoid_cross_entropy_with_logits(x_dec, x), reduction_indices=1)
KL_q_z_x_vs_p_z = - 0.5 * tf.reduce_sum(1 + logsigma2_enc - tf.square(mu_enc) - tf.square(sigma_enc) , reduction_indices=1)


# In[8]:

lower_bound = - KL_q_z_x_vs_p_z + log_p_x_z
loss = - tf.reduce_mean(lower_bound)


# In[9]:

train_it = tf.train.AdagradOptimizer(learning_rate=FLAGS.ADAGRAD_LR).minimize(loss)


# In[10]:

# Summaries
loss_summ = tf.scalar_summary("loss", loss)

reshaped_x_init = tf.reshape(x, [FLAGS.MINIBATCH_SIZE, 28, 28, 1])
image_input_summ = tf.image_summary("image_input", reshaped_x_init, FLAGS.NO_IMG_TO_SHOW)

reshaped_x_dec = tf.reshape(x_dec, [FLAGS.MINIBATCH_SIZE, 28, 28, 1])
image_dec_summ = tf.image_summary("image_dec", reshaped_x_dec, FLAGS.NO_IMG_TO_SHOW)

summary = tf.merge_all_summaries()


# In[11]:

# Add ops to save and restore all the variables.
saver = tf.train.Saver()


# In[12]:

# Training, Testing

with tf.Session() as sess:
    summary_writer = tf.train.SummaryWriter('logs', graph=sess.graph)
    
    if FLAGS.TRAIN:
        print("Training phase.")
        if os.path.isfile(FLAGS.MODEL_PATH):
            os.remove(FLAGS.MODEL_PATH)
            print("Old model removed.")
            
        sess.run(tf.initialize_all_variables())
        print("Initialize parameters.")
        
        for it in xrange(FLAGS.NUMBER_ITERATIONS):
            minibatch = mnist.train.next_batch(FLAGS.MINIBATCH_SIZE)[0]
            cur_train_it, cur_loss_summ, cur_loss = sess.run([train_it, loss_summ, loss], feed_dict={x: minibatch})
            summary_writer.add_summary(cur_loss_summ, it)

            if (it + 1) % 50 == 0 or (it + 1) == FLAGS.NUMBER_ITERATIONS:
                saver.save(sess, FLAGS.MODEL_PATH)
                print("Iteration {0} | Loss: {1}".format(it + 1, cur_loss))
        print("")
        
    if FLAGS.TEST:
        print("Testing phase.")
        if not os.path.isfile(FLAGS.MODEL_PATH):
            print("No model found. Please add training phase.")
        else:    
            saver.restore(sess, FLAGS.MODEL_PATH)
            print("Model restored.")
            
            x_init = mnist.test.next_batch(FLAGS.MINIBATCH_SIZE)[0]
            cur_x_dec, cur_image_input_summ, cur_image_dec_summ = sess.run([x_dec, image_input_summ, image_dec_summ], feed_dict={x: x_init})
            
            summary_writer.add_summary(cur_image_input_summ)
            summary_writer.add_summary(cur_image_dec_summ)
                
                
            
            
        print("")
            
    


# In[ ]:




# In[ ]:



