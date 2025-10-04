from safetensors import safe_open
import os

file_path = os.path.expanduser("~/models/flux1-dev-fp8.safetensors")

# Open the safetensors file
with safe_open(file_path, framework="pt") as f:
    keys = f.keys()
    print("Keys in the checkpoint:")
    for key in keys:
        tensor = f.get_tensor(key)
        print(f"{key}: {tensor.shape}")
