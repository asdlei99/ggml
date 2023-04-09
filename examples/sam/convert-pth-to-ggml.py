# Convert a SAM model checkpoint to a ggml compatible file
#

import os
import sys
import code
import json
import torch
import struct
import numpy as np

if len(sys.argv) < 3:
    print("Usage: convert-pth-to-ggml.py file-model ftype\n")
    print("  ftype == 0 -> float32")
    print("  ftype == 1 -> float16")
    sys.exit(1)

# output in the same directory as the model
fname_model = sys.argv[1]
fname_out   = os.path.dirname(fname_model) + "/ggml-model.bin"

# possible data types
#   ftype == 0 -> float32
#   ftype == 1 -> float16
#
# map from ftype to string
ftype_str = ["f32", "f16"]

ftype = 1
if len(sys.argv) > 2:
    ftype = int(sys.argv[2])

if ftype < 0 or ftype > 1:
    print("Invalid ftype: " + str(ftype))
    sys.exit(1)

fname_out = fname_out.replace(".bin", "-" + ftype_str[ftype] + ".bin")

model = torch.load(fname_model, map_location="cpu")

# TODO: determine based on model data
# TODO: add decoder / prompt encoder if needed
hparams = {
    "n_enc_state":  768,
    "n_enc_layers":  12,
    "n_enc_heads":   12,
}

print(hparams)

for k, v in model.items():
    print(k, v.shape)

exit()
#code.interact(local=locals())

fout = open(fname_out, "wb")

fout.write(struct.pack("i", 0x67676d6c)) # magic: ggml in hex
fout.write(struct.pack("i", hparams["n_enc_state"]))
fout.write(struct.pack("i", hparams["n_enc_layers"]))
fout.write(struct.pack("i", hparams["n_enc_heads"]))
fout.write(struct.pack("i", ftype))

for k, v in model.items():
    name = k
    shape = v.shape

    # skip layers.X.attention.inner_attention.rope.freqs
    #if name[-5:] == "freqs":
    #    continue

    print("Processing variable: " + name + " with shape: ", shape, " and type: ", v.dtype)

    #data = tf.train.load_variable(dir_model, name).squeeze()
    data = v.numpy().squeeze()
    n_dims = len(data.shape);

    # for efficiency - transpose some matrices
    # "model/h.*/attn/c_attn/w"
    # "model/h.*/attn/c_proj/w"
    # "model/h.*/mlp/c_fc/w"
    # "model/h.*/mlp/c_proj/w"
    #if name[-14:] == "/attn/c_attn/w" or \
    #   name[-14:] == "/attn/c_proj/w" or \
    #   name[-11:] == "/mlp/c_fc/w" or \
    #   name[-13:] == "/mlp/c_proj/w":
    #    print("  Transposing")
    #    data = data.transpose()

    dshape = data.shape

    # default type is fp16
    ftype_cur = 1
    if ftype == 0 or n_dims == 1:
        print("  Converting to float32")
        data = data.astype(np.float32)
        ftype_cur = 0
    else:
        print("  Converting to float16")
        data = data.astype(np.float16)

    # header
    str = name.encode('utf-8')
    fout.write(struct.pack("iii", n_dims, len(str), ftype_cur))
    for i in range(n_dims):
        fout.write(struct.pack("i", dshape[n_dims - 1 - i]))
    fout.write(str);

    # data
    data.tofile(fout)

fout.close()

print("Done. Output file: " + fname_out)
print("")