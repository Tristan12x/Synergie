import keras
import numpy as np
import tensorflow as tf
from sklearn.metrics import confusion_matrix

import core.model.model
import core.model.training.loader as loader


class Trainer:
    def __init__(self, dataset : loader.Dataset, model: keras.models.Model, model_filepath: str):
        self.dataset = dataset
        self.model = model

        self.loss_fn = keras.losses.CategoricalCrossentropy()  # from_logits?

        self.accuracy = tf.keras.metrics.CategoricalAccuracy()

        self.model_filepath = model_filepath

    def model_save_best(self, path):
        return keras.callbacks.ModelCheckpoint(
            path,
            monitor='val_accuracy',
            save_best_only=True,
            mode='max'
        )

    def model_load_best(self, path):
        return keras.models.load_model(path)

    def plot(self, trainin, path):
        self.plot_confusion_matrix(path)
        """ plt.plot(trainin.history['loss'], label='training loss')
        plt.plot(trainin.history['val_loss'], label='val loss')
        plt.legend()
        plt.show()

        plt.plot(trainin.history['accuracy'], label='training accuracy')
        plt.plot(trainin.history['val_accuracy'], label='val accuracy')
        plt.legend()
        plt.show() """

    def plot_confusion_matrix(self, path):
        model = self.model_load_best(path)

        y_pred = model.predict(self.dataset.features_test)
        y_pred2 = []
        for x in y_pred:
            y_pred2.append(np.argmax(x))
        y_true = []
        for x in self.dataset.labels_test:
            y_true.append(np.argmax(x))
        results = confusion_matrix(y_true, y_pred2)
        print(results)

        """ n = len(self.dataset.labels_test[0])

        labelled_rows = [constants.jumpType(i).name for i in range(n)]

        df_cm = pd.DataFrame(results)
        # plt.figure(figsize=(10,7))
        sn.set(font_scale=0.9)  # for label size
        sn.heatmap(df_cm, annot=True, annot_kws={"size": 16})  # font size

        plt.show() """

        """ TP = np.diag(results)

        FP = np.sum(results, axis=0) - TP

        FN = np.sum(results, axis=1) - TP

        # display sensitivity and specificity global and for each class

        print("sensitivity: ", TP / (TP + FN))

        print("specificity: ", TP / (TP + FP))

        for i in range(n):
            print(
                f"{constants.jumpType(i).name}: sensitivity: {TP[i] / (TP[i] + FN[i])}, specificity: {TP[i] / (TP[i] + FP[i])}") """

    def train(self, epochs: int = 100, plot: bool = True):
        """
        Do the training, and plot the confusion matrix and losses through epochs
        :param epochs:
        :param plot:
        :return: none
        """

        self.model.summary()

        # callback = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=5)
        # signal.signal(signal.SIGINT, signal_handler)
        try:
            trainin = self.model.fit(
                self.dataset.features_train,
                self.dataset.labels_train,
                epochs=epochs,
                validation_data=self.dataset.val_dataset,
                callbacks=[self.model_save_best(self.model_filepath)],
            )
        except KeyboardInterrupt:
            self.plot(trainin, self.model_filepath)

        if plot:
            self.model = core.model.model.load_model(self.model_filepath)
            self.plot(trainin,self.model_filepath)