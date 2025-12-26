"""
Custom YOLO modules for yolo12m-v2.pt model
Defines A2C2f and C3k2 modules that are missing in older Ultralytics versions
"""
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)

class Conv(nn.Module):
    """Standard convolution with batch normalization and activation."""
    def __init__(self, c1, c2, k=1, s=1, p=None, g=1, d=1, act=True):
        super().__init__()
        if p is None:
            p = k // 2 if isinstance(k, int) else [x // 2 for x in k]
        self.conv = nn.Conv2d(c1, c2, k, s, p, groups=g, dilation=d, bias=False)
        self.bn = nn.BatchNorm2d(c2)
        self.act = nn.SiLU() if act is True else (act if isinstance(act, nn.Module) else nn.Identity())

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))


class Bottleneck(nn.Module):
    """Standard bottleneck block."""
    def __init__(self, c1, c2, shortcut=True, g=1, e=0.5):
        super().__init__()
        c_ = int(c2 * e)
        self.cv1 = Conv(c1, c_, 1, 1)
        self.cv2 = Conv(c_, c2, 3, 1, g=g)
        self.add = shortcut and c1 == c2

    def forward(self, x):
        return x + self.cv2(self.cv1(x)) if self.add else self.cv2(self.cv1(x))


class C3k(nn.Module):
    """C3k module as seen in the model architecture - needs to handle different channel configurations."""
    def __init__(self, c1, c2, n=1, shortcut=True, g=1, e=0.5):
        super().__init__()
        
        self.cv1 = Conv(c1, c2 // 2, 1, 1) 
        self.cv2 = Conv(c1, c2 // 2, 1, 1)  
        self.m = nn.Sequential(*(Bottleneck(c2 // 2, c2 // 2, shortcut, g, e=1.0) for _ in range(n)))
        self.cv3 = Conv(c2, c2, 1)  

    def forward(self, x):
        
        y1 = self.m(self.cv1(x))
        y2 = self.cv2(x)
        return self.cv3(torch.cat((y1, y2), 1))


class C3k2(nn.Module):
    """C3k2 module - Modified version that matches the actual model architecture."""
    def __init__(self, c1, c2, n=1, shortcut=True, g=1, e=0.5):
        super().__init__()
      
        self.cv1 = Conv(c1, c1, 1, 1)  
        self.m = nn.ModuleList([C3k(c1 // 2, c1 // 2, n, shortcut, g, e=1.0)])
        self.cv2 = Conv(c1 + c1 // 2, c2, 1, 1)

    def forward(self, x):
        y1 = self.cv1(x)  
        
        chunk_size = y1.shape[1] // 2
        y1_part = y1[:, :chunk_size, :, :]  
        y2 = self.m[0](y1_part)  
        y_concat = torch.cat((y1, y2), 1)
        return self.cv2(y_concat)


class AAttn(nn.Module):
    """Attention mechanism for A2C2f - matches model architecture."""
    def __init__(self, c1):
        super().__init__()
        self.qkv = Conv(c1, c1 * 3, 1, 1, act=False)
        self.proj = Conv(c1, c1, 1, 1, act=False)
        self.pe = Conv(c1, c1, 7, 1, 3, groups=c1, act=False)

    def forward(self, x):
        B, C, H, W = x.shape
        qkv = self.qkv(x).reshape(B, 3, C, H * W).permute(1, 0, 2, 3)
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        attn = (q @ k.transpose(-2, -1)) * (C ** -0.5)
        attn = attn.softmax(dim=-1)
        x = (attn @ v).transpose(1, 2).reshape(B, C, H, W)
        x = self.proj(x)
        x = x + self.pe(x)
        return x


class ABlock(nn.Module):
    """Attention block for A2C2f - matches model architecture."""
    def __init__(self, c1, c2):
        super().__init__()
        self.attn = AAttn(c1)
        self.mlp = nn.Sequential(
            Conv(c1, c2, 1, 1),
            Conv(c2, c1, 1, 1, act=False)
        )

    def forward(self, x):
        x = x + self.attn(x)
        x = x + self.mlp(x)
        return x


class A2C2f(nn.Module):
    """A2C2f module - Attention-based C2f module with proper ModuleList handling."""
    def __init__(self, c1, c2, n=1, shortcut=False, g=1, e=0.5):
        super().__init__()
      
        self.c = c1 // 2 
        self.cv1 = Conv(c1, self.c, 1, 1)
        self.cv2 = Conv((n + 1) * self.c, c2, 1)
        
       
        self.m = nn.ModuleList()
        for _ in range(n):
            
            block = nn.Sequential(
                ABlock(self.c, 2 * self.c),  
                ABlock(self.c, 2 * self.c)   
            )
            self.m.append(block)

    def forward(self, x):
        y = [self.cv1(x)]
        for module in self.m:
            y.append(module(y[-1]))
        return self.cv2(torch.cat(y, 1))


class DWConv(nn.Module):
    """Depthwise convolution."""
    def __init__(self, c1, c2, k=1, s=1, p=None):
        super().__init__()
        if p is None:
            p = k // 2
        self.conv = nn.Conv2d(c1, c2, k, s, p, groups=c1, bias=False)
        self.bn = nn.BatchNorm2d(c2)
        self.act = nn.SiLU()

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))



def register_custom_modules():
    """
    Register custom modules with torch's serialization system.
    This MUST be called BEFORE loading any model.
    """
    try:
        import sys
        import ultralytics.nn.modules.block as block
        
      
        block.A2C2f = A2C2f
        block.C3k2 = C3k2
        block.C3k = C3k
        block.Conv = Conv
        block.Bottleneck = Bottleneck
        block.AAttn = AAttn
        block.ABlock = ABlock
        block.DWConv = DWConv
        
       
        sys.modules['ultralytics.nn.modules.block'].A2C2f = A2C2f
        sys.modules['ultralytics.nn.modules.block'].C3k2 = C3k2
        sys.modules['ultralytics.nn.modules.block'].C3k = C3k
        sys.modules['ultralytics.nn.modules.block'].AAttn = AAttn
        sys.modules['ultralytics.nn.modules.block'].ABlock = ABlock
        sys.modules['ultralytics.nn.modules.block'].DWConv = DWConv
        
        logger.info("✅ Custom modules registered with Ultralytics")
        
       
        import torch
        torch.serialization.add_safe_globals([
            A2C2f, C3k2, C3k, Conv, Bottleneck, 
            AAttn, ABlock, DWConv
        ])
        
        logger.info("✅ Custom modules registered with torch.serialization")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to register custom modules: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Test the modules
    logging.basicConfig(level=logging.INFO)
    register_custom_modules()
    
    # Test forward pass
    test_input = torch.randn(1, 128, 640, 640)
    
    c3k = C3k(128, 128, n=2)
    print(f"C3k output shape: {c3k(test_input).shape}")
    
    c3k2 = C3k2(128, 256)
    print(f"C3k2 output shape: {c3k2(torch.randn(1, 128, 640, 640)).shape}")
    
    a2c2f = A2C2f(512, 512, n=2)
    print(f"A2C2f output shape: {a2c2f(torch.randn(1, 512, 640, 640)).shape}")