from kaldi.asr import MappedLatticeFasterRecognizer
from kaldi.decoder import LatticeFasterDecoderOptions
from kaldi.matrix import Matrix
from kaldi.util.table import SequentialMatrixReader, DoubleMatrixWriter
from kaldi.nnet3 import NnetSimpleComputationOptions
from kaldi.alignment import MappedAligner
from kaldi.fstext import SymbolTable
from kaldi.lat.align import WordBoundaryInfoNewOpts, WordBoundaryInfo
from pytorch_models import *
import torch
import numpy as np
import pickle

# Set the paths and read/write specifiers
acoustic_model_path = "model.pt"
transition_model_path = "0013_librispeech_v1/exp/chain_cleaned/tdnn_1d_sp/final.mdl"
tree = '0013_librispeech_v1/exp/chain_cleaned/tdnn_1d_sp/tree'
disam = '0013_librispeech_v1/data/lang_chain/phones/disambig.int'
lang_graph ='0013_librispeech_v1/data/lang_chain/L.fst' 
graph_path = "HCLG.fst"
symbols_path = '0013_librispeech_v1/data/lang_chain/words.txt'
phones = '0013_librispeech_v1/exp/chain_cleaned/tdnn_1d_sp/phones.txt'
text_path = 'epadb/test/text' 



mfccs_rspec = ("ark:epadb/test/data/raw_mfcc_test.1.ark")
ivectors_rspec = ("ark:epadb/test/data/ivector_online.1.ark")

loglikes_wspec = "ark:loglikes.ark"

aligner = MappedAligner.from_files(transition_model_path, tree, lang_graph, symbols_path,
                                 disam, acoustic_scale = 1.0)
phones = SymbolTable.read_text(phones)
wb_info = WordBoundaryInfo.from_file(WordBoundaryInfoNewOpts(),
                                     "0013_librispeech_v1/data/lang_test_tgmed/phones/word_boundary.int")


# Instantiate the PyTorch acoustic model (subclass of torch.nn.Module)
model = FTDNN()
model.load_state_dict(torch.load(acoustic_model_path))
model.eval()

loglikes_dict = {}
# Extract the features, decode and write output lattices
with SequentialMatrixReader(mfccs_rspec) as mfccs_reader, \
 	 SequentialMatrixReader(ivectors_rspec) as ivectors_reader, open(text_path) as t, \
     DoubleMatrixWriter(loglikes_wspec) as loglikes_writer:
    for (mkey, mfccs), (ikey, ivectors), line in zip(mfccs_reader, ivectors_reader, t):
        tkey, text = line.strip().split(None, 1)
        ivectors = np.repeat(ivectors, 10, axis=0)
        ivectors = ivectors[:mfccs.shape[0],:]
        x = np.concatenate((mfccs,ivectors), axis=1)
        x = np.expand_dims(x, axis=0)
        feats = torch.from_numpy(x)  # Convert to PyTorch tensor
        loglikes = model(feats)                  # Compute log-likelihoods
#        loglikes_dict[mkey] = loglikes
        loglikes = Matrix(loglikes.detach().numpy()[0])      # Convert to PyKaldi matrix
        loglikes_writer[mkey] = loglikes
        out = aligner.align(loglikes, text)
        phone_alignment = aligner.to_phone_alignment(out["alignment"], phones)
        print(mkey + ' phones', phone_alignment)
        print(mkey + ' transitions', out['alignment'])
        word_alignment = aligner.to_word_alignment(out["best_path"], wb_info)

#with open('loglikes.pickle', 'wb') as handle:
#    pickle.dump(loglikes_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
