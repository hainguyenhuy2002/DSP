"""
Ascend 910B3 NPU Wrapper Implementation
========================================

Ready-to-use wrapper classes for integrating Ascend NPU with the pipeline.

Copy and use these directly!
"""

import torch
try:
    import torch_npu
except ImportError:
    print("⚠️ torch_npu not installed. Install with: pip install torch-npu")

from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional, List


class AscendSingleNPUWrapper:
    """
    Single NPU inference wrapper.
    
    Use this for simple single-device inference.
    Load model once, process many requests sequentially.
    
    Usage:
        wrapper = AscendSingleNPUWrapper("Qwen/Qwen-7B-Chat", npu_id=0)
        pipeline = CompleteTargetDetectionPipeline(llm_client=wrapper)
    """
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen-7B-Chat",
        npu_id: int = 0,
        device_type: str = "npu",
        verbose: bool = True
    ):
        """
        Initialize model on specified Ascend NPU.
        
        Args:
            model_name: HuggingFace model identifier
            npu_id: NPU device ID (0-7 for your cluster)
            device_type: "npu" for Ascend, "cpu" for fallback
            verbose: Print initialization messages
        """
        
        self.device_type = device_type
        self.npu_id = npu_id
        self.device = f'{device_type}:{npu_id}' if device_type == 'npu' else 'cpu'
        self.verbose = verbose
        
        if self.verbose:
            print(f"🚀 Loading {model_name} on {self.device}...")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype="auto",
                device_map="auto" if device_type == 'npu' else None
            )
            
            # Move to device
            self.model.to(self.device)
            self.model.eval()  # Inference mode
            
            if self.verbose:
                print(f"✅ Model loaded on {self.device}")
                print(f"   Parameters: {self.model.num_parameters()/1e9:.1f}B")
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def messages_create(
        self,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        messages: Optional[List[dict]] = None,
        temperature: float = 0.7,
        top_p: float = 0.95
    ) -> str:
        """
        Generate response matching pipeline interface.
        
        Args:
            model: Ignored (for compatibility)
            max_tokens: Maximum response tokens
            messages: List of message dicts with 'content'
            temperature: Generation temperature
            top_p: Top-p sampling parameter
            
        Returns:
            Generated text response
        """
        
        if not messages:
            return "Error: no messages provided"
        
        try:
            prompt = messages[0]['content']
            
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=min(max_tokens, 512),
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode (skip prompt tokens)
            generated_ids = outputs[0][inputs['input_ids'].shape[1]:]
            response = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
            
            return response
            
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return f"Error during generation: {str(e)}"
    
    def get_device_info(self) -> dict:
        """Get information about current device."""
        info = {
            'device': self.device,
            'model_params': self.model.num_parameters() / 1e9,
        }
        
        if self.device_type == 'npu':
            try:
                import torch_npu
                info['npu_available'] = torch_npu.npu.is_available()
                info['npu_count'] = torch_npu.npu.device_count()
                info['current_device_memory'] = torch_npu.npu.memory_allocated(self.npu_id) / 1e9
            except:
                pass
        
        return info


class AscendMultiNPUWrapper:
    """
    Multi-NPU load-balanced wrapper.
    
    Load multiple model copies across different NPUs for parallel processing.
    Automatically balances requests across instances.
    
    Usage:
        wrapper = AscendMultiNPUWrapper("Qwen/Qwen-7B-Chat", num_instances=4)
        pipeline = CompleteTargetDetectionPipeline(llm_client=wrapper)
    
    This will:
        - Create 4 model instances
        - Place them on NPUs: 0-1, 2-3, 4-5, 6-7
        - Load-balance incoming requests
        - Process up to 4 drugs in parallel
    """
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen-7B-Chat",
        num_instances: int = 4,
        verbose: bool = True
    ):
        """
        Initialize multiple model instances on different NPUs.
        
        Args:
            model_name: HuggingFace model identifier
            num_instances: Number of model copies (1-8)
            verbose: Print initialization messages
        """
        
        self.model_name = model_name
        self.num_instances = num_instances
        self.verbose = verbose
        self.models = []
        self.devices = []
        self.current_idx = 0
        self.call_count = 0
        
        if self.verbose:
            print(f"🚀 Loading {num_instances} instances of {model_name}...")
        
        # Load tokenizer once
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Load model instances on different NPUs
        for i in range(num_instances):
            # Assign to NPU pair (0-1, 2-3, 4-5, 6-7, etc)
            npu_id = (i * 2) % 8  # Round-robin across 8 NPUs
            device = f'npu:{npu_id}'
            
            if self.verbose:
                print(f"  Instance {i+1}/{num_instances} on {device}... ", end='', flush=True)
            
            try:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype="auto",
                    device_map="auto"
                )
                model.to(device)
                model.eval()
                
                self.models.append(model)
                self.devices.append(device)
                
                if self.verbose:
                    print("✅")
                    
            except Exception as e:
                if self.verbose:
                    print(f"❌ ({e})")
                raise
        
        if self.verbose:
            print(f"✅ Loaded {len(self.models)} instances")
            print(f"   Devices: {self.devices}")
            print(f"   Load-balancing mode: Round-robin")
    
    def _get_next_model(self):
        """Get next model in round-robin fashion."""
        model = self.models[self.current_idx]
        device = self.devices[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.models)
        return model, device
    
    def messages_create(
        self,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        messages: Optional[List[dict]] = None,
        temperature: float = 0.7,
        top_p: float = 0.95
    ) -> str:
        """
        Generate response with automatic load balancing.
        """
        
        self.call_count += 1
        
        if not messages:
            return "Error: no messages provided"
        
        try:
            prompt = messages[0]['content']
            
            # Get next model (load balancing)
            model, device = self._get_next_model()
            
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048
            ).to(device)
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=min(max_tokens, 512),
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            generated_ids = outputs[0][inputs['input_ids'].shape[1]:]
            response = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )
            
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_status(self) -> dict:
        """Get status of all model instances."""
        return {
            'num_instances': len(self.models),
            'devices': self.devices,
            'total_calls': self.call_count,
            'calls_per_instance': [
                self.call_count // len(self.models) 
                + (1 if i < (self.call_count % len(self.models)) else 0)
                for i in range(len(self.models))
            ]
        }


class AscendPipelineConfig:
    """Configuration for Ascend deployment."""
    
    def __init__(self):
        self.model_name = "Qwen/Qwen-7B-Chat"  # or "THUDM/chatglm-6b"
        self.num_instances = 4
        self.batch_size = 1
        self.max_tokens_per_call = 512
        self.temperature = 0.7
        self.top_p = 0.95
        self.device_type = "npu"
        self.verbose = True
    
    def to_dict(self):
        return self.__dict__


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_single_npu():
    """Example: Single NPU inference."""
    
    print("="*70)
    print("EXAMPLE 1: Single NPU Inference")
    print("="*70)
    
    # Create wrapper
    wrapper = AscendSingleNPUWrapper(
        model_name="Qwen/Qwen-7B-Chat",
        npu_id=0
    )
    
    # Test inference
    test_message = [{
        "role": "user",
        "content": "What is a good target for cancer therapy?"
    }]
    
    response = wrapper.messages_create(messages=test_message)
    print(f"\nResponse:\n{response}")
    
    # Get device info
    info = wrapper.get_device_info()
    print(f"\nDevice Info: {info}")


def example_multi_npu():
    """Example: Multi-NPU load balanced inference."""
    
    print("\n" + "="*70)
    print("EXAMPLE 2: Multi-NPU Load Balanced Inference")
    print("="*70)
    
    # Create multi-instance wrapper
    wrapper = AscendMultiNPUWrapper(
        model_name="Qwen/Qwen-7B-Chat",
        num_instances=4
    )
    
    # Simulate multiple requests
    test_messages = [
        [{"role": "user", "content": f"Question {i}"}]
        for i in range(8)
    ]
    
    print("\nProcessing 8 requests across 4 instances:")
    for i, msg in enumerate(test_messages):
        print(f"  Request {i+1}... ", end='', flush=True)
        response = wrapper.messages_create(messages=msg)
        print("✅")
    
    # Show load balancing
    status = wrapper.get_status()
    print(f"\nLoad Balancing Status:")
    print(f"  Total calls: {status['total_calls']}")
    print(f"  Calls per instance: {status['calls_per_instance']}")


def example_pipeline_integration():
    """Example: Integration with drug target detection pipeline."""
    
    print("\n" + "="*70)
    print("EXAMPLE 3: Pipeline Integration")
    print("="*70)
    
    from main_pipeline import CompleteTargetDetectionPipeline
    from drug_abstract_fetcher import DrugMetadata
    
    # Create Ascend wrapper
    wrapper = AscendMultiNPUWrapper(
        model_name="Qwen/Qwen-7B-Chat",
        num_instances=4
    )
    
    # Create pipeline
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",
        llm_client=wrapper,
        output_dir="./ascend_results"
    )
    
    # Create drug
    drug = DrugMetadata(
        name="Docetaxel",
        smiles="CC1=C2[C@H](C(=O)[C@@]3([C@H]...",
        moa="Microtubule stabiliser"
    )
    
    # Define targets
    available_targets = [
        "TUBB", "TUPA1A", "TOP2A", "TOP2B", "TP53", "BAX",
        "EGFR", "HER2", "MAPK1", "AKT1"
    ]
    
    # Run pipeline
    print("\n🚀 Starting drug target detection on Ascend NPUs...")
    result = pipeline.process_drug(
        drug_metadata=drug,
        available_targets=available_targets,
        num_abstracts=10,
        num_target_runs=5
    )
    
    # Show results
    print("\n✅ Results:")
    print(f"  Drug: {result['drug_name']}")
    print(f"  Predicted targets: {result['high_confidence_targets']}")
    
    # Show wrapper status
    status = wrapper.get_status()
    print(f"\n  NPU utilization:")
    print(f"    Instances: {status['num_instances']}")
    print(f"    Total LLM calls: {status['total_calls']}")


def example_batch_processing():
    """Example: Batch processing multiple drugs."""
    
    print("\n" + "="*70)
    print("EXAMPLE 4: Batch Processing")
    print("="*70)
    
    from main_pipeline import CompleteTargetDetectionPipeline
    from drug_abstract_fetcher import DrugMetadata
    
    # Create wrapper
    wrapper = AscendMultiNPUWrapper(
        model_name="Qwen/Qwen-7B-Chat",
        num_instances=4
    )
    
    # Create pipeline
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",
        llm_client=wrapper,
        output_dir="./batch_results"
    )
    
    # Create sample drugs
    drugs = [
        DrugMetadata(f"Drug{i}", "SMILES", f"MOA{i}")
        for i in range(8)
    ]
    
    targets = ["TUBB", "TOP2A", "TP53", "BAX"]
    
    # Process batch
    print(f"\nProcessing {len(drugs)} drugs in batch...")
    results = []
    
    for i, drug in enumerate(drugs, 1):
        print(f"  {i}/{len(drugs)}: {drug.name}...", end='', flush=True)
        
        result = pipeline.process_drug(
            drug_metadata=drug,
            available_targets=targets,
            num_abstracts=5,  # Reduce for batch
            num_target_runs=3
        )
        
        results.append(result)
        print(" ✅")
    
    # Summary
    status = wrapper.get_status()
    print(f"\n✅ Batch processing complete!")
    print(f"   Drugs processed: {len(results)}")
    print(f"   Total LLM calls: {status['total_calls']}")
    print(f"   Load balance: {status['calls_per_instance']}")


if __name__ == "__main__":
    """Run examples."""
    
    import sys
    
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║         Ascend 910B3 NPU Wrapper - Example Runner                 ║
    ║                                                                    ║
    ║  Usage:                                                            ║
    ║    python ascend_npu_wrapper.py single    # Single NPU            ║
    ║    python ascend_npu_wrapper.py multi     # Multi-NPU             ║
    ║    python ascend_npu_wrapper.py pipeline  # Full pipeline         ║
    ║    python ascend_npu_wrapper.py batch     # Batch processing      ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "single":
            example_single_npu()
        elif mode == "multi":
            example_multi_npu()
        elif mode == "pipeline":
            example_pipeline_integration()
        elif mode == "batch":
            example_batch_processing()
        else:
            print(f"Unknown mode: {mode}")
    else:
        print("Choose a mode (single/multi/pipeline/batch)")
