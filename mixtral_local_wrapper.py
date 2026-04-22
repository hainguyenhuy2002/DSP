"""
COMPLETE GUIDE: RUN PIPELINE WITH LOCAL MIXTRAL MODEL
======================================================

Your setup:
  ✅ You have: Mixtral model at /villa/rhh25/mixtral
  ✅ You want: Run drug target detection pipeline with this model
  ✅ Goal: Process drugs and get target predictions

This guide shows you exactly how to do it!
"""

# ============================================================================
# STEP 1: CREATE WRAPPER FOR YOUR LOCAL MIXTRAL MODEL
# ============================================================================

"""
File: mixtral_local_wrapper.py
"""

import torch

try:
    import torch_npu
except ImportError:
    print("⚠️ torch_npu not available, will use CPU/GPU")

from pathlib import Path

from transformers import AutoModelForCausalLM, AutoTokenizer


class LocalMixtralWrapper:
    """
    Wrapper for local Mixtral model.

    Uses your downloaded model at /villa/rhh25/mixtral
    Compatible with the drug target detection pipeline.

    Usage:
        wrapper = LocalMixtralWrapper(model_path="/villa/rhh25/mixtral")
        # Then use with pipeline
    """

    def __init__(
        self,
        model_path: str = "/villa/rhh25/mixtral",
        device: str = "npu:0",  # Change to "cuda:0" for GPU or "cpu"
        verbose: bool = True,
    ):
        """
        Initialize local Mixtral model.

        Args:
            model_path: Path to local Mixtral model directory
            device: Device to load on ("npu:0", "cuda:0", "cpu", etc.)
            verbose: Print status messages
        """

        self.model_path = Path(model_path)
        self.device = device
        self.verbose = verbose

        # Verify model exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model path not found: {model_path}")

        if self.verbose:
            print(f"🚀 Loading local Mixtral model from {model_path}...")
            print(f"   Device: {device}")

        try:
            # Load tokenizer from local directory
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path),
                local_files_only=True,  # Use only local files
            )
            if self.verbose:
                print("✅ Tokenizer loaded")

            # Load model from local directory
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                local_files_only=True,  # Use only local files
                torch_dtype=torch.float16,  # Use FP16 for efficiency
                device_map="auto" if device.startswith("npu") else None,
            )

            # Move to device
            if not device.startswith("npu"):
                self.model.to(device)

            self.model.eval()  # Inference mode

            if self.verbose:
                print("✅ Model loaded successfully")
                print(f"   Model parameters: {self.model.num_parameters() / 1e9:.1f}B")

        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise

    def messages_create(
        self, model=None, max_tokens=1000, messages=None, temperature=0.7, top_p=0.95
    ) -> str:
        """
        Generate response (matches pipeline interface).

        Args:
            model: Ignored (for compatibility)
            max_tokens: Maximum response length
            messages: List of message dicts
            temperature: Generation temperature
            top_p: Top-p sampling

        Returns:
            Generated text
        """

        if not messages:
            return "Error: no messages provided"

        try:
            prompt = messages[0]["content"]

            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=2048,
            ).to(self.device)

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=min(max_tokens, 512),
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            # Decode
            generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
            response = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

            return response

        except Exception as e:
            print(f"❌ Generation error: {e}")
            return f"Error: {str(e)}"


# ============================================================================
# STEP 2: CREATE COMPLETE PIPELINE SCRIPT
# ============================================================================

"""
File: run_pipeline_with_mixtral.py

This is the complete script to run the pipeline with your Mixtral model.
"""


def run_pipeline_with_mixtral():
    """
    Complete example: Run drug target detection with local Mixtral.
    """

    import time

    from drug_abstract_fetcher import DrugMetadata
    from main_pipeline import (
        CompleteTargetDetectionPipeline,
        create_example_target_list,
    )
    from mixtral_local_wrapper import LocalMixtralWrapper

    print("=" * 70)
    print("DRUG TARGET DETECTION WITH LOCAL MIXTRAL")
    print("=" * 70)

    # ===== STEP 1: Initialize Mixtral wrapper =====
    print("\n📋 Step 1: Initialize Mixtral Wrapper")
    print("-" * 70)

    try:
        wrapper = LocalMixtralWrapper(
            model_path="/villa/rhh25/mixtral",  # Your model path!
            device="npu:0",  # Change to "cuda:0" for GPU or "cpu"
            verbose=True,
        )
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nPlease verify:")
        print("  1. Path is correct: /villa/rhh25/mixtral")
        print("  2. Model files exist in that directory")
        print("  3. Check: ls -la /villa/rhh25/mixtral/")
        return

    # ===== STEP 2: Create pipeline =====
    print("\n🔧 Step 2: Create Pipeline")
    print("-" * 70)

    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",  # Change this!
        llm_client=wrapper,
        output_dir="./mixtral_results",
    )
    print("✅ Pipeline created")

    # ===== STEP 3: Define available targets =====
    print("\n📂 Step 3: Load Data")
    print("-" * 70)

    # Get available targets (proteins from STRING)
    available_targets = create_example_target_list()
    print(f"✅ Loaded {len(available_targets)} available protein targets")

    # ===== STEP 4: Create sample drug =====
    print("\n💊 Step 4: Create Drug")
    print("-" * 70)

    # Example drug (replace with your actual drug)
    drug = DrugMetadata(
        name="Docetaxel",
        smiles="CC1=C2[C@H](C(=O)[C@@]3([C@H](C[C@@H]4[C@]([C@...",
        moa="Microtubule stabiliser",
        targets=["TUBB"],
    )
    print(f"✅ Created drug: {drug.name}")
    print(f"   MOA: {drug.moa}")
    print(f"   Known targets: {drug.targets}")

    # ===== STEP 5: Run pipeline =====
    print("\n🚀 Step 5: Run Pipeline")
    print("-" * 70)
    print(f"Processing {drug.name}...")
    print("(This will take 5-10 minutes)")
    print()

    start_time = time.time()

    try:
        result = pipeline.process_drug(
            drug_metadata=drug,
            available_targets=available_targets,
            num_abstracts=10,  # Get 10 PubMed abstracts
            num_target_runs=5,  # Run 5 times for self-consistency
        )
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return

    elapsed = time.time() - start_time

    # ===== STEP 6: Display results =====
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\n📊 Drug: {result['drug_name']}")
    print(f"Processing time: {elapsed / 60:.1f} minutes")

    print("\n🎯 High Confidence Targets:")
    for target in result["high_confidence_targets"]:
        print(f"   ✅ {target}")

    if not result["high_confidence_targets"]:
        print("   (No high-confidence targets found)")

    print("\n📈 All Predictions (sorted by confidence):")
    for pred in result["target_detection"]["predictions"][:5]:
        count = pred["count"]
        num_runs = result["target_detection"]["num_runs"]
        print(f"\n   {pred['target']}")
        print(f"     Confidence: {pred['confidence']}")
        print(f"     Appeared in: {count}/{num_runs} runs")
        if pred["rationales"]:
            print(f"     Rationale: {pred['rationales'][0][:100]}...")

    print("\n💾 Results saved to: ./mixtral_results/")

    print("\n" + "=" * 70)
    print("✅ COMPLETE!")
    print("=" * 70)

    return result


# ============================================================================
# STEP 3: BATCH PROCESSING MULTIPLE DRUGS
# ============================================================================

"""
File: batch_process_mixtral.py

Process multiple drugs efficiently with Mixtral.
"""


def batch_process_drugs():
    """
    Process multiple drugs in sequence.
    """

    import json
    import time

    from drug_abstract_fetcher import DrugMetadata
    from main_pipeline import (
        CompleteTargetDetectionPipeline,
        create_example_target_list,
    )
    from mixtral_local_wrapper import LocalMixtralWrapper

    print("=" * 70)
    print("BATCH PROCESSING WITH LOCAL MIXTRAL")
    print("=" * 70)

    # Initialize wrapper (once)
    print("\n📋 Initializing Mixtral model...")
    wrapper = LocalMixtralWrapper(
        model_path="/villa/rhh25/mixtral",
        device="npu:0",  # Or "cuda:0" for GPU
        verbose=True,
    )

    # Create pipeline
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com", llm_client=wrapper, output_dir="./batch_results"
    )

    # Get targets
    available_targets = create_example_target_list()

    # Your drugs (replace with actual data)
    drugs = [
        DrugMetadata("Docetaxel", "SMILES1", moa="MOA1"),
        DrugMetadata("Cisplatin", "SMILES2", moa="MOA2"),
        DrugMetadata("Doxorubicin", "SMILES3", moa="MOA3"),
    ]

    # Process each drug
    results = []
    batch_start = time.time()

    print(f"\n🚀 Processing {len(drugs)} drugs...\n")

    for i, drug in enumerate(drugs, 1):
        print(f"[{i}/{len(drugs)}] {drug.name:20s} ", end="", flush=True)

        drug_start = time.time()

        result = pipeline.process_drug(
            drug_metadata=drug,
            available_targets=available_targets,
            num_abstracts=10,
            num_target_runs=5,
        )

        drug_time = time.time() - drug_start
        results.append(result)

        print(f"✅ ({drug_time / 60:.1f} min)")

    batch_time = time.time() - batch_start

    # Summary
    print("\n" + "=" * 70)
    print("BATCH SUMMARY")
    print("=" * 70)

    print(f"\nTotal drugs processed: {len(results)}")
    print(f"Total time: {batch_time / 60:.1f} minutes")
    print(f"Average per drug: {batch_time / len(results) / 60:.1f} minutes")

    print("\nResults:")
    for result in results:
        targets = result["high_confidence_targets"]
        print(f"  {result['drug_name']:20s} → {targets}")

    # Save summary
    summary = {
        "num_drugs": len(results),
        "total_time_minutes": batch_time / 60,
        "results": [
            {"drug": r["drug_name"], "targets": r["high_confidence_targets"]}
            for r in results
        ],
    }

    with open("./batch_results/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n✅ Summary saved to ./batch_results/summary.json")

    return results


# ============================================================================
# STEP 4: DEVICE SELECTION
# ============================================================================

"""
IMPORTANT: Choose the right device for your hardware!

For Ascend NPU:
  device = "npu:0"      # Single NPU
  device = "npu:1"      # Another NPU
  
For NVIDIA GPU:
  device = "cuda:0"     # GPU 0
  device = "cuda:1"     # GPU 1
  
For CPU only:
  device = "cpu"        # CPU inference (slow)

To check available devices:
  
  # For Ascend
  import torch_npu
  print(f"NPUs available: {torch_npu.npu.device_count()}")
  
  # For NVIDIA
  import torch
  print(f"CUDA available: {torch.cuda.is_available()}")
  print(f"GPUs: {torch.cuda.device_count()}")
"""

# ============================================================================
# STEP 5: COMPLETE QUICK START SCRIPT
# ============================================================================

"""
File: quick_run_mixtral.py

Simplest possible way to run everything.
"""

if __name__ == "__main__":
    import sys

    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║         Drug Target Detection with Local Mixtral Model            ║
    ║                                                                    ║
    ║  Usage:                                                            ║
    ║    python run_pipeline_with_mixtral.py    # Single drug           ║
    ║    python batch_process_mixtral.py        # Multiple drugs        ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)

    # Choose what to run
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "single":
            run_pipeline_with_mixtral()
        elif mode == "batch":
            batch_process_drugs()
        else:
            print(f"Unknown mode: {mode}")
            print("Use: python script.py [single|batch]")
    else:
        # Default: run single drug example
        run_pipeline_with_mixtral()
