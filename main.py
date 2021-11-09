# CS390-NIP GAN lab
# Max Jacobson / Sri Cherukuri / Anthony Niemiec
# FA2020
# uses Fashion MNIST https://www.kaggle.com/zalando-research/fashionmnist 
# uses CIFAR-10 https://www.cs.toronto.edu/~kriz/cifar.html

import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Input, Dense, Reshape, Flatten
from tensorflow.keras.layers import BatchNormalization, LeakyReLU
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Conv2DTranspose, UpSampling2D
from tensorflow.keras.optimizers import Adam
from scipy.misc import imsave
import matplotlib.pyplot as plt
import random

random.seed(1618)
np.random.seed(1618)
tf.compat.v1.set_random_seed(1618)

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# this is the ratio of training the generator to the discriminator
# If it is 1, they will be trained in the same ratio
# If it is something like 3, then the generator will train 3 times every time discriminator is trained once
GENERATOR_TO_DISCRIMINATOR_TRAIN_RATIO = 1

# NOTE: mnist_d is no credit
# NOTE: cifar_10 is extra credit
#DATASET = "mnist_d"
DATASET = "mnist_f"
#DATASET = "cifar_10"

if DATASET == "mnist_d":
    IMAGE_SHAPE = (IH, IW, IZ) = (28, 28, 1)
    LABEL = "numbers"

elif DATASET == "mnist_f":
    IMAGE_SHAPE = (IH, IW, IZ) = (28, 28, 1)
    CLASSLIST = ["top", "trouser", "pullover", "dress", "coat", "sandal", "shirt", "sneaker", "bag", "ankle boot"]
    #LABEL = "coat"
    LABEL = "sneaker"
    #LABEL = "trouser"

elif DATASET == "cifar_10":
    IMAGE_SHAPE = (IH, IW, IZ) = (32, 32, 3)
    CLASSLIST = ["airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck"]
    LABEL = "airplane"

IMAGE_SIZE = IH*IW*IZ

NOISE_SIZE = 100    # length of noise array

# file prefixes and directory
OUTPUT_NAME = DATASET + "_" + LABEL
OUTPUT_DIR = "./outputs/" + OUTPUT_NAME

# NOTE: switch to True in order to receive debug information
VERBOSE_OUTPUT = True

################################### DATA FUNCTIONS ###################################

# Load in and report the shape of dataset
def getRawData():
    if DATASET == "mnist_f":
        (xTrain, yTrain), (xTest, yTest) = tf.keras.datasets.fashion_mnist.load_data()
    elif DATASET == "cifar_10":
        (xTrain, yTrain), (xTest, yTest) = tf.keras.datasets.cifar10.load_data()
    elif DATASET == "mnist_d":
        (xTrain, yTrain), (xTest, yTest) = tf.keras.datasets.mnist.load_data()
    print("Shape of xTrain dataset: %s." % str(xTrain.shape))
    print("Shape of yTrain dataset: %s." % str(yTrain.shape))
    print("Shape of xTest dataset: %s." % str(xTest.shape))
    print("Shape of yTest dataset: %s." % str(yTest.shape))
    return ((xTrain, yTrain), (xTest, yTest))

# Filter out the dataset to only include images with our LABEL, meaning we may also discard
# class labels for the images because we know exactly what to expect
def preprocessData(raw):
    ((xTrain, yTrain), (xTest, yTest)) = raw
    if DATASET == "mnist_d":
        xP = np.r_[xTrain, xTest]
    else:
        c = CLASSLIST.index(LABEL)
        x = np.r_[xTrain, xTest]
        y = np.r_[yTrain, yTest].flatten()
        ilist = [i for i in range(y.shape[0]) if y[i] == c]
        xP = x[ilist]
    # NOTE: Normalize from 0 to 1 or -1 to 1
    #xP = xP/255.0
    xP = xP/127.5 - 1
    print("Shape of Preprocessed dataset: %s." % str(xP.shape))
    return xP


################################### CREATING A GAN ###################################

# Model that discriminates between fake and real dataset images
def buildDiscriminator():
    model = Sequential()
    
    model.add(keras.layers.Conv2D(32, kernel_size = (3, 3), activation = "sigmoid", input_shape = IMAGE_SHAPE))
    model.add(keras.layers.Conv2D(64, kernel_size = (3, 3), activation = "relu"))
    model.add(keras.layers.MaxPooling2D(pool_size = (2, 2)))
    model.add(keras.layers.Dropout(0.2))
    model.add(keras.layers.Conv2D(48, kernel_size = (3, 3), activation = "relu"))
    model.add(keras.layers.Conv2D(64, kernel_size = (3, 3), activation = "relu"))
    model.add(keras.layers.Dropout(0.2))
    model.add(keras.layers.Flatten())
    model.add(keras.layers.Dense(128, activation = "relu"))
    model.add(keras.layers.Dense(64, activation = "relu"))
    model.add(keras.layers.Dense(1, activation = "sigmoid"))

    # Creating a Keras Model out of the network
    inputTensor = Input(shape = IMAGE_SHAPE)
    return Model(inputTensor, model(inputTensor))

# Model that generates a fake image from random noise
def buildGenerator():
    model = Sequential()

    model.add(keras.layers.Reshape((10, 10, 1), input_shape=(NOISE_SIZE,)))
    model.add(keras.layers.Conv2DTranspose(128, kernel_size = (3, 3), activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Conv2DTranspose(64, kernel_size = (5, 5), activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Conv2DTranspose(64, kernel_size = (5, 5), activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Conv2DTranspose(48, kernel_size = (3, 3), activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Conv2DTranspose(48, kernel_size = (5, 5), activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Flatten())
    model.add(keras.layers.Dense(512, activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Dense(1024, activation = "elu"))
    model.add(BatchNormalization(momentum=0.8))
    model.add(keras.layers.Dense(IMAGE_SIZE, activation = "tanh"))
    model.add(Reshape(IMAGE_SHAPE))

    # Creating a Keras Model out of the network
    inputTensor = Input(shape = (NOISE_SIZE,))
    return Model(inputTensor, model(inputTensor))

def buildGAN(images, epochs = 40000, batchSize = 32, loggingInterval = 0):
    # Setup
    opt = Adam(learning_rate=0.0002)
    loss = "binary_crossentropy"

    # Setup adversary
    adversary = buildDiscriminator()
    adversary.compile(loss = loss, optimizer = opt, metrics = ["accuracy"])

    # Setup generator and GAN
    adversary.trainable = False                     # freeze adversary's weights when training GAN
    generator = buildGenerator()                    # generator is trained within GAN in relation to adversary performance
    noise = Input(shape = (NOISE_SIZE,))
    gan = Model(noise, adversary(generator(noise))) # GAN feeds generator into adversary
    gan.compile(loss = loss, optimizer = opt)

    # Training
    trueCol = np.ones((batchSize, 1))
    falseCol = np.zeros((batchSize, 1))

    genLosses = []
    disLosses = []
    epochIncrements = []
    for epoch in range(epochs):

        # Train discriminator with a true and false batch
        batch = images[np.random.randint(0, images.shape[0], batchSize)]
        noise = np.random.normal(0, 1, (batchSize, NOISE_SIZE))
        genImages = generator.predict(noise)

        advLoss = 0
        if epoch % GENERATOR_TO_DISCRIMINATOR_TRAIN_RATIO == 0 or (loggingInterval > 0 and epoch % loggingInterval == 0):
            advTrueLoss = adversary.train_on_batch(batch, trueCol)
            advFalseLoss = adversary.train_on_batch(genImages, falseCol)
            advLoss = np.add(advTrueLoss, advFalseLoss) * 0.5

        # Train generator by training GAN while keeping adversary component constant
        noise = np.random.normal(0, 1, (batchSize, NOISE_SIZE))
        genLoss = gan.train_on_batch(noise, trueCol)

        genLosses.append(genLoss)
        disLosses.append(advLoss[0])
        epochIncrements.append(epoch)

        # Logging
        if loggingInterval > 0 and epoch % loggingInterval == 0:
            print("\tEpoch %d:" % epoch)
            print("\t\tDiscriminator loss: %f." % advLoss[0])
            print("\t\tDiscriminator accuracy: %.2f%%." % (100 * advLoss[1]))
            print("\t\tGenerator loss: %f." % genLoss)
            runGAN(generator, OUTPUT_DIR + "/" + OUTPUT_NAME + "_test_%d.png" % (epoch / loggingInterval))

    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.plot(epochIncrements, genLosses, 'b', label="Generator Loss")
    plt.plot(epochIncrements, disLosses, 'g', label="Discriminator Loss")
    plt.legend()
    plt.savefig(OUTPUT_DIR + "/losses.png")

    return (generator, adversary, gan)

# Generates an image using given generator
def runGAN(generator, outfile):
    noise = np.random.normal(0, 1, (1, NOISE_SIZE)) # generate a random noise array
    img = generator.predict(noise)[0]               # run generator on noise
    img = np.squeeze(img)                           # readjust image shape if needed
    img = (0.5*img + 0.5)*255                       # adjust values to range from 0 to 255 as needed
    imsave(outfile, img)                            # store resulting image


################################### RUNNING THE PIPELINE #############################

def main():
    print("Starting %s image generator program." % LABEL)
    # Make output directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    # Receive all of mnist_f
    raw = getRawData()
    # Filter for just the class we are trying to generate
    data = preprocessData(raw)
    # Create and train all facets of the GAN
    (generator, adv, gan) = buildGAN(data, epochs = 15000, loggingInterval = 1000)
    # Utilize our spooky neural net gimmicks to create realistic counterfeit images
    for i in range(10):
        runGAN(generator, OUTPUT_DIR + "/" + OUTPUT_NAME + "_final_%d.png" % i)
    print("Images saved in %s directory." % OUTPUT_DIR)

if __name__ == '__main__':
    main()