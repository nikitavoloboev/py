import torch
from torch import nn


class TransformerBlock(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(
            embed_dim=d_model, num_heads=num_heads, dropout=dropout, batch_first=True
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
        )
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        # 1) Multi-head self-attention + residual + norm
        attn_out, _ = self.attn(query=x, key=x, value=x, attn_mask=mask)
        x = self.norm1(x + self.dropout(attn_out))
        # 2) Feed-forward + residual + norm
        ffn_out = self.ffn(x)
        x = self.norm2(x + self.dropout(ffn_out))
        return x


if __name__ == "__main__":
    # create a block with model-dim=32, 4 heads, feed-forward dim=64
    block = TransformerBlock(d_model=32, num_heads=4, d_ff=64)
    # batch of 2 sequences, each length 10, embedding dim 32
    x = torch.randn(2, 10, 32)
    out = block(x)  # forward pass
    print("Output shape:", out.shape)  # → (2, 10, 32)
