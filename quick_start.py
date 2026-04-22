#!/usr/bin/env python3
"""
Quick Start Example - Drug Target Detection Pipeline
=====================================================

This script demonstrates the minimal code needed to run both pipelines
for drug target detection.

To use this script:
1. Replace 'your_email@example.com' with your email
2. Set up your LLM client (Anthropic or OpenAI)
3. Run: python quick_start.py
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from drug_abstract_fetcher import DrugMetadata
from main_pipeline import (
    CompleteTargetDetectionPipeline,
    create_few_shot_examples,
    create_example_target_list
)


def quick_start():
    """
    Quick start example showing both pipelines in action.
    """
    
    print("\n" + "="*70)
    print("DRUG TARGET DETECTION PIPELINE - QUICK START")
    print("="*70 + "\n")
    
    # =========================================================================
    # STEP 1: Initialize Pipeline
    # =========================================================================
    
    print("STEP 1: Initializing pipeline...")
    
    # Option A: Without LLM (mock mode for testing)
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",
        llm_client=None,  # Use mock LLM
        output_dir="./quick_start_results"
    )
    
    # Option B: With Anthropic Claude (uncomment to use)
    # from anthropic import Anthropic
    # client = Anthropic()
    # pipeline = CompleteTargetDetectionPipeline(
    #     email="your_email@example.com",
    #     llm_client=client,
    #     output_dir="./quick_start_results"
    # )
    
    print("✓ Pipeline initialized\n")
    
    # =========================================================================
    # STEP 2: Add Few-Shot Learning Examples
    # =========================================================================
    
    print("STEP 2: Adding few-shot learning examples...")
    
    # Create examples
    examples = create_few_shot_examples()
    
    # Add them to the pipeline
    for example in examples.get_examples(num_examples=3):
        pipeline.add_few_shot_example(
            drug_name=example['drug_name'],
            drug_description=example['drug_description'],
            targets=example['targets'],
            rationale=example['rationale']
        )
    
    print(f"✓ Added {len(examples.examples)} training examples\n")
    
    # =========================================================================
    # STEP 3: Prepare Available Targets
    # =========================================================================
    
    print("STEP 3: Loading available protein targets...")
    
    available_targets = create_example_target_list()
    print(f"✓ Loaded {len(available_targets)} target proteins\n")
    print(f"  Sample targets: {', '.join(available_targets[:5])}...\n")
    
    # =========================================================================
    # STEP 4: Create Drug to Process
    # =========================================================================
    
    print("STEP 4: Creating drug metadata...")
    
    # Example 1: Docetaxel
    docetaxel = DrugMetadata(
        name="Docetaxel",
        smiles="CC1=C2[C@H](C(=O)[C@@]3([C@H](C[C@@H]4[C@]([C@...",
        inchi_key="UJNXZPHOMNTTOO-NOCBQZHGSA-N",
        moa="Microtubule stabiliser",
        targets=["TUBB"]
    )
    
    print(f"✓ Created drug: {docetaxel.name}")
    print(f"  MOA: {docetaxel.moa}")
    print(f"  Known targets: {docetaxel.targets}\n")
    
    # =========================================================================
    # STEP 5: Run Complete Pipeline
    # =========================================================================
    
    print("STEP 5: Running complete pipeline...\n")
    print("-"*70)
    
    result = pipeline.process_drug(
        drug_metadata=docetaxel,
        available_targets=available_targets,
        num_abstracts=3,  # Reduced for quick start
        num_target_runs=2,  # Reduced for demo
        num_predictions_per_run=5,
        save_intermediate=True
    )
    
    print("-"*70 + "\n")
    
    # =========================================================================
    # STEP 6: Display Results
    # =========================================================================
    
    print("STEP 6: Results Summary\n")
    
    print(f"Drug: {result['drug_name']}")
    print(f"Status: ✓ Processing Complete\n")
    
    # Show description summary
    print("PHASE 1: DRUG DESCRIPTION")
    print("-"*70)
    description = result['description']['refined_description'][:300]
    print(f"Refined Description:\n{description}...\n")
    
    # Show target predictions
    print("PHASE 2: TARGET PREDICTIONS")
    print("-"*70)
    print(f"High Confidence Targets: {result['high_confidence_targets']}\n")
    
    predictions = result['target_detection']['predictions']
    print("All Predictions (ranked by confidence):")
    for i, pred in enumerate(predictions[:5], 1):
        count = pred['count']
        num_runs = result['target_detection']['num_runs']
        print(f"\n{i}. {pred['target']}")
        print(f"   Confidence: {pred['confidence']}")
        print(f"   Appearances: {count}/{num_runs} runs")
        if pred['rationales']:
            print(f"   Rationale: {pred['rationales'][0][:80]}...")
    
    # =========================================================================
    # STEP 7: Access Output Files
    # =========================================================================
    
    print("\n" + "="*70)
    print("OUTPUT FILES")
    print("="*70)
    
    output_dir = Path("./quick_start_results")
    if output_dir.exists():
        files = list(output_dir.glob("*"))
        if files:
            print(f"\nResults saved to: {output_dir.absolute()}\n")
            for file in files:
                print(f"  - {file.name}")
        else:
            print("\nNo output files found (running in mock mode)")
    
    print("\n" + "="*70 + "\n")


def advanced_example():
    """
    Advanced example showing how to process multiple drugs.
    """
    
    print("\n" + "="*70)
    print("ADVANCED EXAMPLE - BATCH PROCESSING")
    print("="*70 + "\n")
    
    # Initialize pipeline
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",
        llm_client=None,
        output_dir="./batch_results"
    )
    
    # Add examples
    examples = create_few_shot_examples()
    for example in examples.get_examples():
        pipeline.add_few_shot_example(
            drug_name=example['drug_name'],
            drug_description=example['drug_description'],
            targets=example['targets']
        )
    
    # Get targets
    available_targets = create_example_target_list()
    
    # Create multiple drugs
    drugs = [
        DrugMetadata(
            name="Docetaxel",
            smiles="CC1=C2[C@H]...",
            moa="Microtubule stabiliser",
            targets=["TUBB"]
        ),
        DrugMetadata(
            name="Cisplatin",
            smiles="N.N.Cl[Pt]Cl",
            moa="DNA crosslinker",
            targets=["DNA"]
        ),
        DrugMetadata(
            name="Doxorubicin",
            smiles="C1=C2C(=C...",
            moa="Topoisomerase II inhibitor",
            targets=["TOP2A", "TOP2B"]
        ),
    ]
    
    print(f"Processing {len(drugs)} drugs...\n")
    
    # Process all drugs
    results = pipeline.process_multiple_drugs(
        drugs=drugs,
        available_targets=available_targets,
        num_abstracts=3,
        num_target_runs=2,
        num_predictions_per_run=5
    )
    
    # Print summary
    print("\n" + "="*70)
    print("BATCH PROCESSING SUMMARY")
    print("="*70 + "\n")
    
    for result in results:
        print(f"Drug: {result['drug_name']}")
        print(f"  → Predicted targets: {result['high_confidence_targets']}")
        print(f"  → Total predictions: {len(result['target_detection']['predictions'])}")
        print()
    
    # Save summary
    pipeline.save_summary(results, filename="batch_summary.json")
    print("\nSummary saved to: batch_summary.json")


def customize_example():
    """
    Example showing how to customize the pipeline with your own examples.
    """
    
    print("\n" + "="*70)
    print("CUSTOMIZATION EXAMPLE")
    print("="*70 + "\n")
    
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",
        llm_client=None,
        output_dir="./custom_results"
    )
    
    # Add custom few-shot examples
    print("Adding custom few-shot examples...\n")
    
    pipeline.add_few_shot_example(
        drug_name="CustomDrug1",
        drug_description="A selective inhibitor of kinase XYZ that blocks...",
        targets=["KINASE_XYZ", "KINASE_ABC"],
        rationale="Directly inhibits ATP binding pocket of kinase XYZ"
    )
    
    pipeline.add_few_shot_example(
        drug_name="CustomDrug2",
        drug_description="A monoclonal antibody targeting protein ABC...",
        targets=["PROTEIN_ABC", "PROTEIN_DEF"],
        rationale="Binds to extracellular domain of protein ABC"
    )
    
    print("✓ Added 2 custom examples\n")
    
    # Process drug
    drug = DrugMetadata(
        name="MyCustomDrug",
        smiles="CUSTOM_SMILES_STRING",
        moa="Custom mechanism",
        targets=[]
    )
    
    available_targets = [
        "KINASE_XYZ", "KINASE_ABC", "PROTEIN_ABC", "PROTEIN_DEF",
        "TARGET_1", "TARGET_2", "TARGET_3"
    ]
    
    print("Processing drug with custom configuration...\n")
    
    result = pipeline.process_drug(
        drug_metadata=drug,
        available_targets=available_targets,
        num_abstracts=2,
        num_target_runs=2,
        num_predictions_per_run=3
    )
    
    print(f"\nPredicted targets for {drug.name}:")
    for target in result['high_confidence_targets']:
        print(f"  ✓ {target}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Drug Target Detection Pipeline - Quick Start"
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "batch", "custom"],
        default="quick",
        help="Which example to run"
    )
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        quick_start()
    elif args.mode == "batch":
        advanced_example()
    elif args.mode == "custom":
        customize_example()
    
    print("\n" + "="*70)
    print("For more information, see README_COMPREHENSIVE_GUIDE.py")
    print("="*70 + "\n")
