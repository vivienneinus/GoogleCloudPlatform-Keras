# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# MobileNet 224 + Composable (2017)
# Note: 224 refers to the image size, not the number of layers
# Paper: https://arxiv.org/pdf/1704.04861.pdf

import tensorflow as tf
from tensorflow.keras import Input, Model
from tensorflow.keras.layers import ZeroPadding2D, Conv2D, BatchNormalization, ReLU
from tensorflow.keras.layers import DepthwiseConv2D, GlobalAveragePooling2D, Reshape, Dropout

class MobileNetV1(object):
    """ Construct a Mobile Convolution Neural Network """
    # Meta-parameter: width multiplier (0 .. 1) for reducing number of filters.
    alpha      = 1   
    # Meta-parameter: resolution multiplier (0 .. 1) for reducing input size
    pho        = 1
    # Meta-parameter: dropout rate
    dropout    = 0.5 
    init_weights='glorot_uniform'
    _model = None

    def __init__(self, alpha=1, pho=1, dropout=0.5, input_shape=(224, 224, 3), n_classes=1000):
        """ Construct a Mobile Convolution Neural Network
            alpha      : width multipler
            pho        :
            input_shape: the input shape
            n_classes  : number of output classes
        """
        if alpha < 0 or alpha > 1:
            raise Exception("MobileNet: alpha out of range")
        if pho < 0 or pho > 1:
            raise Exception("MobileNet: pho out of range")
        if dropout < 0 or dropout > 1:
            raise Exception("MobileNet: alpha out of range")
        
        inputs = Input(shape=(int(input_shape[0] * pho), int(input_shape[1] * pho), 3))

        # The Stem Group
        x = self.stem(inputs, alpha)    

        # The Learner
        x = self.learner(x, alpha)

        # The classifier 
        outputs = self.classifier(x, alpha, dropout, n_classes)

        # Instantiate the Model
        self._model = Model(inputs, outputs)

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, _model):
        self._model - _model
    
    def stem(self, inputs, alpha):
        """ Construct the Stem Group
            inputs : input tensor
            alpha  : width multiplier
        """
        # Convolutional block
        x = ZeroPadding2D(padding=((0, 1), (0, 1)))(inputs)
        x = Conv2D(32 * alpha, (3, 3), strides=(2, 2), padding='valid', use_bias=False, kernel_initializer=self.init_weights)(x)
        x = BatchNormalization()(x)
        x = ReLU(6.0)(x)

        # Depthwise Separable Convolution Block
        x = MobileNetV1.depthwise_block(x, 64, alpha, (1, 1))
        return x
    
    def learner(self, x, alpha):
        """ Construct the Learner
            x      : input to the learner
            alpha  : width multiplier
        """
        # First Depthwise Separable Convolution Group
        x = MobileNetV1.group(x, 128, 2, alpha)

        # Second Depthwise Separable Convolution Group
        x = MobileNetV1.group(x, 256, 2, alpha)

        # Third Depthwise Separable Convolution Group
        x = MobileNetV1.group(x, 512, 6, alpha)

        # Fourth Depthwise Separable Convolution Group
        x = MobileNetV1.group(x, 1024, 2, alpha)
        return x

    @staticmethod
    def group(x, n_filters, n_blocks, alpha, init_weights=None):
        """ Construct a Depthwise Separable Convolution Group
            x         : input to the group
            n_filters : number of filters
            n_blocks  : number of blocks in the group
            alpha     : width multiplier
        """   
        # In first block, the depthwise convolution is strided - feature map size reduction
        x = MobileNetV1.depthwise_block(x, n_filters, alpha, strides=(2, 2), init_weights=init_weights)
    
        # Remaining blocks
        for _ in range(n_blocks - 1):
            x = MobileNetV1.depthwise_block(x, n_filters, alpha, strides=(1, 1), init_weights=init_weights)
        return x

    @staticmethod
    def depthwise_block(x, n_filters, alpha, strides, init_weights=None):
        """ Construct a Depthwise Separable Convolution block
            x         : input to the block
            n_filters : number of filters
            alpha     : width multiplier
            strides   : strides
        """
        if init_weights is None:
            init_weights = MobileNetV1.init_weights
            
        # Apply the width filter to the number of feature maps
        filters = int(n_filters * alpha)

        # Strided convolution to match number of filters
        if strides == (2, 2):
            x = ZeroPadding2D(padding=((0, 1), (0, 1)))(x)
            padding = 'valid'
        else:
            padding = 'same'

        # Depthwise Convolution
        x = DepthwiseConv2D((3, 3), strides, padding=padding, use_bias=False, kernel_initializer=init_weights)(x)
        x = BatchNormalization()(x)
        x = ReLU(6.0)(x)

        # Pointwise Convolution
        x = Conv2D(filters, (1, 1), strides=(1, 1), padding='same', use_bias=False, kernel_initializer=init_weights)(x)
        x = BatchNormalization()(x)
        x = ReLU(6.0)(x)
        return x

    def classifier(self, x, alpha, dropout, n_classes):
        """ Construct the classifier group
            x         : input to the classifier
            alpha     : width multiplier
            dropout   : dropout percentage
            n_classes : number of output classes
        """
        # Flatten the feature maps into 1D feature maps (?, N)
        x = GlobalAveragePooling2D()(x)

        # Reshape the feature maps to (?, 1, 1, 1024)
        shape = (1, 1, int(1024 * alpha))
        x = Reshape(shape)(x)
        # Perform dropout for preventing overfitting
        x = Dropout(dropout)(x)

        # Use convolution for classifying (emulates a fully connected layer)
        x = Conv2D(n_classes, (1, 1), padding='same', activation='softmax', kernel_initializer=self.init_weights)(x)
        # Reshape the resulting output to 1D vector of number of classes
        x = Reshape((n_classes, ))(x)
        return x

# Example
# mobilenet = MobileNetV1()
