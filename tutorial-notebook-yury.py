# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# + [markdown] _uuid="7edff2eb-50cb-4285-8255-b3262dbd5161" _cell_guid="5c1b75ee-94f3-40c8-adbe-4ca8325b9f9c"
# Natural Language Inferencing (NLI) is a classic NLP (Natural Language Processing) problem that involves taking two sentences (the _premise_ and the _hypothesis_ ), and deciding how they are related- if the premise entails the hypothesis, contradicts it, or neither.
#
# In this tutorial we'll look at the _Contradictory, My Dear Watson_ competition dataset, build a preliminary model using Tensorflow 2, Keras, and BERT, and prepare a submission file.

# + _uuid="d3a20929-8e1d-48d2-869c-cc57f8c63cc9" _cell_guid="20666a1f-e31b-4134-94f8-fea9a50998d3"
# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python Docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)

# Input data files are available in the read-only "../input/" directory
# For example, running this (by clicking run or pressing Shift+Enter) will list all files under the input directory

import os
for dirname, _, filenames in os.walk('/kaggle/input'):
    for filename in filenames:
        print(os.path.join(dirname, filename))

# You can write up to 5GB to the current directory (/kaggle/working/) that gets preserved as output when you create a version using "Save & Run All" 
# You can also write temporary files to /kaggle/temp/, but they won't be saved outside of the current session
# -

os.environ["WANDB_API_KEY"] = "0" ## to silence warning

# + _uuid="e3dd507b-c502-488c-9dd0-419c5d73c159" _cell_guid="863de620-d4b7-4711-b587-e1c75be9e36f"
from transformers import BertTokenizer, TFBertModel
import matplotlib.pyplot as plt
import tensorflow as tf

# + [markdown] _uuid="58fb9ec5-c099-494c-bf59-6ec9d6e64628" _cell_guid="6c5122f9-8c39-4892-81a9-1f8830b64484"
# Let's set up our TPU.

# + _uuid="386d0823-63ab-4765-9561-32c5f382e71d" _cell_guid="ca2729e3-9275-4a9c-b150-592320bd3e54"
try:
    tpu = tf.distribute.cluster_resolver.TPUClusterResolver()
    tf.config.experimental_connect_to_cluster(tpu)
    tf.tpu.experimental.initialize_tpu_system(tpu)
    strategy = tf.distribute.experimental.TPUStrategy(tpu)
except ValueError:
    strategy = tf.distribute.get_strategy() # for CPU and single GPU
    print('Number of replicas:', strategy.num_replicas_in_sync)

# + [markdown] _uuid="0b64130f-530a-4560-8afd-462a55fc14b3" _cell_guid="44a1d22f-053c-4188-b25f-d714aa745016"
# ## Downloading Data

# + [markdown] _uuid="b9285071-38f2-421b-9b1c-9c44d41c7365" _cell_guid="6fb2939c-b14a-450f-85dd-7220439eaf55"
# The training set contains a premise, a hypothesis, a label (0 = entailment, 1 = neutral, 2 = contradiction), and the language of the text. For more information about what these mean and how the data is structured, check out the data page: https://www.kaggle.com/c/contradictory-my-dear-watson/data

# + _uuid="6e60d19f-aeae-417a-a10a-50cc1d5ee685" _cell_guid="f3ad567b-a156-4ffc-a6f8-1f5e6e989a4e"
train = pd.read_csv("../input/contradictory-my-dear-watson/train.csv")
# -

# We can use the pandas head() function to take a quick look at the training set.

# + _uuid="82e6d183-b8e1-412b-816f-c9020bac1428" _cell_guid="d3b9a632-7abb-4bef-acd3-9cba577dc2c0"
train.head()

# + [markdown] _uuid="abfb11e9-865c-4b50-b0cc-9d25851618ff" _cell_guid="817c2470-9778-46e8-be86-fdd1b9449b93"
# Let's look at one of the pairs of sentences.

# + _uuid="dea716f0-9698-4a10-a7f1-1a0bb36054db" _cell_guid="bcca3548-bb15-4868-86ec-95fe084d6e06"
train.premise.values[1]

# + _uuid="5b639eff-aeea-4dca-b516-7e729cdeb741" _cell_guid="15dcbe6c-4914-4400-a8fd-65b6e4cbf652"
train.hypothesis.values[1]

# + _uuid="c63a91e0-05f7-4a67-acf8-2131ef50f054" _cell_guid="e16e8879-c565-4a29-bacc-26648659da29"
train.label.values[1]

# + [markdown] _uuid="216dc9c2-1699-4b89-af27-443d1b4c7289" _cell_guid="8c9122ea-797d-48f1-b4ba-85bc2e0e6f18"
# These statements are contradictory, and the label shows that.
#
# Let's look at the distribution of languages in the training set.

# + _uuid="7243f511-d81e-436c-971f-6328b7c0cf43" _cell_guid="7d9b43ef-4ac1-40d5-aebc-a162f1b9a6c0"
labels, frequencies = np.unique(train.language.values, return_counts = True)

plt.figure(figsize = (10,10))
plt.pie(frequencies,labels = labels, autopct = '%1.1f%%')
plt.show()

# + [markdown] _uuid="68cee874-838e-4f0e-9f80-bfebc4a295d0" _cell_guid="a7f5d429-083e-4d81-883f-e032dfb0e236"
# ## Preparing Data for Input

# + [markdown] _uuid="27e66828-76b9-44f4-ba79-66fe0cb8f922" _cell_guid="f20a33db-a377-43b6-825e-157456ed1092"
# To start out, we can use a pretrained model. Here, we'll use a multilingual BERT model from huggingface. For more information about BERT, see: https://github.com/google-research/bert/blob/master/multilingual.md
#
# First, we download the tokenizer.

# + _uuid="0af7b876-e719-474a-b6a5-fef500624b83" _cell_guid="ddc3e65e-24a4-43dc-98f0-194655d17cfd"
model_name = 'bert-base-multilingual-cased'
tokenizer = BertTokenizer.from_pretrained(model_name)


# + [markdown] _uuid="a6088f3d-8778-4a6c-82b0-db6a5461ec95" _cell_guid="f6f4ab91-c9b5-4861-a400-89969200b7f4"
# Tokenizers turn sequences of words into arrays of numbers. Let's look at an example:

# + _uuid="2cd597c4-6204-44ba-869a-fbf7c32c711d" _cell_guid="55838dc3-c459-4097-b5b2-44d049429e25"
def encode_sentence(s):
   tokens = list(tokenizer.tokenize(s))
   tokens.append('[SEP]')
   return tokenizer.convert_tokens_to_ids(tokens)


# + _uuid="797de062-6743-4455-9ead-73527bf6c3b6" _cell_guid="f05a9baa-b7fa-44da-89dd-04fdfc149cba"
encode_sentence("I love machine learning")


# + [markdown] _uuid="1fb6acf3-3c19-494e-83bd-84d6d933e6f0" _cell_guid="e80e3fcd-513e-4d14-88fd-9417b746c107"
# BERT uses three kind of input data- input word IDs, input masks, and input type IDs.
#
# These allow the model to know that the premise and hypothesis are distinct sentences, and also to ignore any padding from the tokenizer.
#
# We add a [CLS] token to denote the beginning of the inputs, and a [SEP] token to denote the separation between the premise and the hypothesis. We also need to pad all of the inputs to be the same size. For more information about BERT inputs, see: https://huggingface.co/transformers/model_doc/bert.html#tfbertmodel
#
# Now, we're going to encode all of our premise/hypothesis pairs for input into BERT.

# + _uuid="dedb18d0-63cb-492b-8fe0-b4ebb8819e4c" _cell_guid="037b0a29-3e6d-42b6-b13a-328fab19d15d"
def bert_encode(hypotheses, premises, tokenizer):
    
  num_examples = len(hypotheses)
  
  sentence1 = tf.ragged.constant([
      encode_sentence(s)
      for s in np.array(hypotheses)])
  sentence2 = tf.ragged.constant([
      encode_sentence(s)
       for s in np.array(premises)])

  cls = [tokenizer.convert_tokens_to_ids(['[CLS]'])]*sentence1.shape[0]
  input_word_ids = tf.concat([cls, sentence1, sentence2], axis=-1)

  input_mask = tf.ones_like(input_word_ids).to_tensor()

  type_cls = tf.zeros_like(cls)
  type_s1 = tf.zeros_like(sentence1)
  type_s2 = tf.ones_like(sentence2)
  input_type_ids = tf.concat(
      [type_cls, type_s1, type_s2], axis=-1).to_tensor()

  inputs = {
      'input_word_ids': input_word_ids.to_tensor(),
      'input_mask': input_mask,
      'input_type_ids': input_type_ids}

  return inputs


# + _uuid="697579c5-9f89-421c-8cbc-4321a7c93179" _cell_guid="fc14d779-d0c6-4585-8e80-ebf539bd132c"
train_input = bert_encode(train.premise.values, train.hypothesis.values, tokenizer)

# + [markdown] _uuid="e1bf9ee4-e872-45d8-a118-a72eb7917d8b" _cell_guid="3dbd7066-6469-4823-8e09-e2dfa0a68bcc"
# ## Creating & Training Model

# + [markdown] _uuid="33811793-9df3-4d97-84c3-c5367a130cd7" _cell_guid="7ebc4032-48bf-4bbd-8244-6b4ee38a1f56"
# Now, we can incorporate the BERT transformer into a Keras Functional Model. For more information about the Keras Functional API, see: https://www.tensorflow.org/guide/keras/functional.
#
# This model was inspired by the model in this notebook: https://www.kaggle.com/tanulsingh077/deep-learning-for-nlp-zero-to-transformers-bert#BERT-and-Its-Implementation-on-this-Competition, which is a wonderful introduction to NLP!

# + _uuid="1094f3ff-6b5b-4b15-9d93-b0065ae586bd" _cell_guid="69f90af1-4d66-4b83-a264-df23a3a68e26"
max_len = 50

def build_model():
    bert_encoder = TFBertModel.from_pretrained(model_name)
    input_word_ids = tf.keras.Input(shape=(max_len,), dtype=tf.int32, name="input_word_ids")
    input_mask = tf.keras.Input(shape=(max_len,), dtype=tf.int32, name="input_mask")
    input_type_ids = tf.keras.Input(shape=(max_len,), dtype=tf.int32, name="input_type_ids")
    
    embedding = bert_encoder([input_word_ids, input_mask, input_type_ids])[0]
    output = tf.keras.layers.Dense(3, activation='softmax')(embedding[:,0,:])
    
    model = tf.keras.Model(inputs=[input_word_ids, input_mask, input_type_ids], outputs=output)
    model.compile(tf.keras.optimizers.Adam(lr=1e-5), loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    
    return model


# + _uuid="47c8cc2f-a7b9-4bae-971b-e41277b45c8b" _cell_guid="97885b33-70f1-4d14-b788-fd1a650d5a57"
with strategy.scope():
    model = build_model()
    model.summary()

# + _uuid="316f4376-9df7-40ea-bbbd-ae46eb5562e5" _cell_guid="0423d993-8ff5-4ab9-bc47-87e1cb74c0c5"
model.fit(train_input, train.label.values, epochs = 2, verbose = 1, batch_size = 64, validation_split = 0.2)

# + _uuid="3bfd96e9-cf2c-41ad-bdcc-8c31408f05bd" _cell_guid="e26cba08-7fe9-4e2e-ab2e-062a26a5fcac"
test = pd.read_csv("../input/contradictory-my-dear-watson/test.csv")
test_input = bert_encode(test.premise.values, test.hypothesis.values, tokenizer)

# + _uuid="9f040800-653f-4f51-9f60-0456d89068be" _cell_guid="4b871234-9a42-4f5e-9792-7fc90615b808"
test.head()

# + [markdown] _uuid="fb1ff888-7684-4888-b861-3c31a3f360b7" _cell_guid="87b18b05-30f3-45f9-9c3e-6f8184934bd0"
# ## Generating & Submitting Predictions

# + _uuid="f9db46a1-1f83-4ddb-85bf-da8f40afe623" _cell_guid="a7ab0c33-0377-4cb2-b4f9-fc489383fdb7"
predictions = [np.argmax(i) for i in model.predict(test_input)]

# + [markdown] _uuid="7b489c00-896d-44af-9371-16c2cf222365" _cell_guid="1d0e8e42-2746-4331-95a5-3eb78ca6861c"
# The submission file will consist of the ID column and a prediction column. We can just copy the ID column from the test file, make it a dataframe, and then add our prediction column.

# + _uuid="9e0e34fa-1ef7-4207-a5c3-c21863c7be27" _cell_guid="add7302f-ae26-4e78-b69d-858cacb35991"
submission = test.id.copy().to_frame()
submission['prediction'] = predictions

# + _uuid="1d4999aa-10d2-4a88-962a-8f10bded837b" _cell_guid="d4fdefdc-4839-4962-ae75-6807390a6de7"
submission.head()

# + _uuid="b8463f7e-8b2f-4c24-8eb3-a35ec02a2d6e" _cell_guid="84abe9e3-ef04-4dac-97d2-2308a0f11313"
submission.to_csv("submission.csv", index = False)

# + [markdown] _uuid="1af8c748-a13d-4274-9208-94d9895fdc19" _cell_guid="4d057f53-824d-400f-b9f0-5adfc06322ef"
# And now we've created our submission file, which can be submitted to the competition. Good luck!
