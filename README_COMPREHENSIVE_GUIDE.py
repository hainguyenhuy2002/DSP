"""
DRUG TARGET DETECTION PIPELINE - COMPREHENSIVE GUIDE
=====================================================

This documentation describes the complete drug target detection pipeline,
which combines drug description generation with few-shot learning for 
target prediction.

"""

# ============================================================================
# 1. ARCHITECTURE OVERVIEW
# ============================================================================

"""
The pipeline follows the architecture shown in the provided figure:

┌─────────────────────────────────────────────────────────────────────────┐
│                    DRUG TARGET DETECTION PIPELINE                       │
└─────────────────────────────────────────────────────────────────────────┘

PHASE 1: DESCRIPTION GENERATION (Pipeline 1)
==============================================

Step 1: Input Drug Information
  └─> Drug Name, SMILES, InChI Key, MOA, Known Targets

Step 2: PubMed Abstract Fetching
  └─> Fetch K abstracts from PubMed using Entrez API
  └─> Filter for relevance and remove duplicates

Step 3: Initial Description Generation
  └─> LLM generates description from metadata (drug name, MOA, targets)
  └─> Focuses on basic mechanism of action

Step 4: Description Refinement
  └─> LLM refines description using PubMed abstracts
  └─> Incorporates recent literature findings
  └─> Output: Refined Drug Description


PHASE 2: TARGET DETECTION (Pipeline 2)
=======================================

Step 5: Few-Shot Learning Setup
  └─> Load bank of example drugs with known targets
  └─> Format examples for LLM context
  └─> Available target list (from STRING interaction database)

Step 6: Target Prediction (Run K times)
  └─> LLM predicts targets using:
      - Refined drug description
      - Few-shot examples
      - Constrained selection from available targets
  └─> Generates rationales for each prediction

Step 7: Self-Consistency Aggregation
  └─> Aggregate predictions across K runs
  └─> Calculate appearance frequency for each target
  └─> Assign confidence levels

Step 8: Final Target List
  └─> Output: Ranked targets with confidence scores and rationales


"""

# ============================================================================
# 2. MODULE STRUCTURE
# ============================================================================

"""
MODULE 1: drug_abstract_fetcher.py
==================================
Classes:
  - DrugAbstractFetcher: Fetches PubMed abstracts using Entrez API
  - DrugMetadata: Container for drug metadata (name, SMILES, MOA, targets)

Key Functions:
  - fetch_abstracts(drug_name, num_abstracts): Retrieve abstracts from PubMed
  - format_abstracts(abstracts): Format for LLM inclusion


MODULE 2: pipeline_1_description_generation.py
================================================
Classes:
  - DrugDescription: Container for generated descriptions
  - DrugDescriptionGenerator: Generates initial descriptions from metadata
  - DrugDescriptionRefiner: Refines descriptions using abstracts
  - DescriptionGenerationPipeline: Main orchestrator for Phase 1

Key Functions:
  - generate_initial_description(drug_metadata): Create initial description
  - refine_description(initial_desc, abstracts): Refine using literature
  - run(drug_metadata, num_abstracts): Execute complete Phase 1


MODULE 3: pipeline_2_target_detection.py
========================================
Classes:
  - TargetPrediction: Container for single target prediction
  - TargetDetectionResult: Container for complete detection results
  - FewShotExampleBank: Repository of drug-target training examples
  - TargetDetector: Performs target predictions using few-shot learning
  - SelfConsistencyAggregator: Aggregates predictions across multiple runs
  - TargetDetectionPipeline: Main orchestrator for Phase 2

Key Functions:
  - predict_targets(description, targets, num_predictions): Predict in one run
  - aggregate(predictions_list, num_runs): Combine results from K runs
  - get_confidence_level(count, num_runs): Compute confidence score
  - run(drug_name, description, targets, num_runs): Execute complete Phase 2


MODULE 4: main_pipeline.py
==========================
Classes:
  - CompleteTargetDetectionPipeline: Integrates both phases

Key Functions:
  - process_drug(metadata, targets): Run complete pipeline for one drug
  - process_multiple_drugs(drugs, targets): Process multiple drugs
  - save_summary(results): Save aggregated results


"""

# ============================================================================
# 3. QUICK START GUIDE
# ============================================================================

"""
INSTALLATION
============

1. Install required dependencies:
   pip install biopython requests tqdm pandas

2. For LLM support, install one of:
   pip install anthropic          # For Claude API
   pip install openai             # For OpenAI API


BASIC USAGE
===========

from drug_abstract_fetcher import DrugMetadata
from main_pipeline import CompleteTargetDetectionPipeline, create_example_target_list
from anthropic import Anthropic

# Initialize
client = Anthropic()
pipeline = CompleteTargetDetectionPipeline(
    email="your_email@example.com",
    llm_client=client,
    output_dir="./results"
)

# Add few-shot examples
pipeline.add_few_shot_example(
    drug_name="Docetaxel",
    drug_description="Microtubule-stabilizing agent...",
    targets=["TUBB", "TUBA1A"],
    rationale="Binds to β-tubulin"
)

# Define available targets
available_targets = [
    "TUBB", "TUBA1A", "TOP2A", "TP53", "BAX", "EGFR", ...
]

# Create drug metadata
drug = DrugMetadata(
    name="MyDrug",
    smiles="C1=CC=C...",
    moa="Cell cycle inhibitor",
    targets=["TUBB"]
)

# Run complete pipeline
result = pipeline.process_drug(
    drug_metadata=drug,
    available_targets=available_targets,
    num_abstracts=10,
    num_target_runs=5
)

# Access results
print(f"High confidence targets: {result['high_confidence_targets']}")


"""

# ============================================================================
# 4. DETAILED USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: Process Single Drug
===============================

from drug_abstract_fetcher import DrugMetadata, DrugAbstractFetcher
from pipeline_1_description_generation import DescriptionGenerationPipeline
from anthropic import Anthropic

# Step 1: Create drug metadata
docetaxel = DrugMetadata(
    name="Docetaxel",
    smiles="CC1=C2[C@H]...",
    moa="Microtubule stabilisation",
    targets=["TUBB"]
)

# Step 2: Initialize Anthropic client
client = Anthropic()

# Step 3: Generate description
pipeline = DescriptionGenerationPipeline(
    email="user@example.com",
    llm_client=client
)
description = pipeline.run(docetaxel, num_abstracts=10)

# Step 4: Access results
print(f"Drug: {description.drug_name}")
print(f"Refined Description: {description.refined_description}")
print(f"Abstracts Retrieved: {len(description.abstracts)}")


EXAMPLE 2: Detect Targets with Few-Shot Learning
==================================================

from pipeline_2_target_detection import (
    TargetDetectionPipeline, FewShotExampleBank
)
from anthropic import Anthropic

# Create example bank
examples = FewShotExampleBank()
examples.add_example(
    drug_name="Docetaxel",
    drug_description="Microtubule-stabilizing...",
    targets=["TUBB", "TUBA1A"],
    rationale="Binds to β-tubulin"
)
examples.add_example(
    drug_name="Doxorubicin",
    drug_description="Topoisomerase II inhibitor...",
    targets=["TOP2A", "TOP2B"],
    rationale="Inhibits DNA re-ligation"
)

# Initialize pipeline
client = Anthropic()
pipeline = TargetDetectionPipeline(llm_client=client, example_bank=examples)

# Run target detection
available_targets = ["TUBB", "TUBA1A", "TOP2A", "TOP2B", "TP53", ...]
result = pipeline.run(
    drug_name="TestDrug",
    drug_description="A novel inhibitor targeting microtubules...",
    available_targets=available_targets,
    num_runs=5,
    num_predictions_per_run=5
)

# Access high-confidence targets
high_conf = result.get_high_confidence_targets()
print(f"Predicted targets: {high_conf}")

# View detailed predictions
for pred in result.predictions:
    print(f"{pred.target}: {pred.confidence.value} ({pred.count}/{result.num_runs})")
    print(f"  Rationale: {pred.rationales[0]}")


EXAMPLE 3: Batch Process Multiple Drugs
========================================

from main_pipeline import CompleteTargetDetectionPipeline, create_example_target_list
from drug_abstract_fetcher import DrugMetadata
from anthropic import Anthropic

# Initialize pipeline
client = Anthropic()
pipeline = CompleteTargetDetectionPipeline(
    email="user@example.com",
    llm_client=client,
    output_dir="./batch_results"
)

# Create list of drugs
drugs = [
    DrugMetadata("Docetaxel", "CC1=C2...", moa="Microtubule stabiliser"),
    DrugMetadata("Cisplatin", "N.N.Cl[Pt]Cl", moa="DNA crosslinker"),
    DrugMetadata("Doxorubicin", "C1=C...", moa="Topoisomerase inhibitor"),
]

# Get available targets
targets = create_example_target_list()

# Process all drugs
results = pipeline.process_multiple_drugs(
    drugs=drugs,
    available_targets=targets,
    num_abstracts=10,
    num_target_runs=5
)

# Save summary
pipeline.save_summary(results, filename="batch_summary.json")

# Access results for each drug
for result in results:
    print(f"{result['drug_name']}: {result['high_confidence_targets']}")


"""

# ============================================================================
# 5. CONFIGURATION AND PARAMETERS
# ============================================================================

"""
KEY PARAMETERS
===============

Abstract Fetching:
  - num_abstracts: Number of PubMed abstracts to fetch (default: 10)
    * Higher values provide more context but take longer
    * Recommended: 5-20 for balance

Few-Shot Learning:
  - num_examples: Number of training examples to include (default: 3)
    * More examples improve consistency but add context length
    * Recommended: 3-5 examples

Target Prediction:
  - num_runs: Number of independent prediction runs for self-consistency (default: 5)
    * Higher values improve confidence but increase API costs
    * Recommended: 5-10 runs
  
  - num_predictions_per_run: Targets to predict each run (default: 5)
    * Balances coverage with focus on relevant targets
    * Recommended: 3-10 targets per run
  
  - num_examples_in_prompt: Few-shot examples for LLM (default: 3)
    * More examples provide better guidance
    * Recommended: 2-5 examples

Confidence Thresholds:
  - VERY_HIGH: appears in 4-5 runs (80% confidence)
  - HIGH: appears in 3 runs (60% confidence)
  - MEDIUM: appears in 2 runs (40% confidence)
  - LOW: appears in 1 run (20% confidence)


OPTIMIZATION TIPS
=================

For Speed (Minimum Latency):
  - num_abstracts = 5
  - num_target_runs = 3
  - num_predictions_per_run = 3
  - Estimated time: 2-3 minutes per drug

For Accuracy (Maximum Reliability):
  - num_abstracts = 15-20
  - num_target_runs = 10
  - num_predictions_per_run = 7-8
  - Estimated time: 15-20 minutes per drug

For Balance (Recommended):
  - num_abstracts = 10
  - num_target_runs = 5
  - num_predictions_per_run = 5
  - Estimated time: 5-10 minutes per drug


"""

# ============================================================================
# 6. OUTPUT FORMATS
# ============================================================================

"""
PHASE 1: Drug Description Output
=================================

DrugDescription object contains:
  - drug_name: Name of the drug
  - initial_description: First LLM-generated description
  - refined_description: Enhanced description incorporating abstracts
  - abstracts: List of PubMed abstracts retrieved
  - metadata: Original drug metadata

Saved as JSON:
{
  "drug_name": "Docetaxel",
  "initial_description": "...",
  "refined_description": "...",
  "abstracts": ["Abstract 1...", "Abstract 2...", ...],
  "metadata": {
    "name": "Docetaxel",
    "smiles": "...",
    "moa": "Microtubule stabilisation",
    "targets": ["TUBB"]
  }
}


PHASE 2: Target Detection Output
=================================

TargetDetectionResult contains:
  - drug_name: Drug name
  - predictions: List of TargetPrediction objects
  - num_runs: Number of prediction runs performed
  - available_targets: All possible targets

Each TargetPrediction contains:
  - target: Target protein name
  - confidence: Confidence level (very_high, high, medium, low)
  - count: Appearances across runs
  - rationales: List of explanations from the LLM

Saved as JSON:
{
  "drug_name": "Docetaxel",
  "predictions": [
    {
      "target": "TUBB",
      "confidence": "very_high",
      "count": 5,
      "rationales": [
        "Directly binds and stabilizes tubulin...",
        "Prevents microtubule disassembly..."
      ],
      "metadata": {"num_runs": 5}
    },
    ...
  ],
  "num_runs": 5,
  "available_targets": ["TUBB", "TUPA1A", ...]
}


SUMMARY OUTPUT
==============

Saved for batch processing:
{
  "num_drugs": 3,
  "drugs": [
    {
      "name": "Docetaxel",
      "targets": ["TUBB", "TUPA1A"],
      "num_predictions": 8
    },
    ...
  ]
}


"""

# ============================================================================
# 7. ERROR HANDLING AND DEBUGGING
# ============================================================================

"""
COMMON ISSUES AND SOLUTIONS
============================

Issue 1: No PubMed Abstracts Found
  Cause: Drug name not recognized by NCBI
  Solution: Use alternative drug names (generics, brand names)
  
  Example:
    # Instead of:
    DrugMetadata(name="Acronym Only")
    # Use:
    DrugMetadata(name="Full Drug Name (Brand Name)")

Issue 2: LLM API Errors
  Cause: Invalid API key, rate limiting, or connection issues
  Solution: Check credentials and add retry logic
  
  Example:
    import time
    from tenacity import retry, stop_after_attempt, wait_exponential
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential())
    def call_with_retry(prompt):
        return llm.messages.create(...)

Issue 3: Target Prediction Too Broad
  Cause: Few-shot examples not specific enough
  Solution: Add more targeted examples
  
  Example:
    # Add more domain-specific examples
    bank.add_example(
        drug_name="SimilarDrug",
        drug_description="Similar mechanism...",
        targets=["TUBB"],
        rationale="Specific binding mechanism..."
    )

Issue 4: Memory Issues with Large Batches
  Cause: Processing too many drugs simultaneously
  Solution: Process in smaller batches
  
  Example:
    batch_size = 5
    for i in range(0, len(drugs), batch_size):
        batch = drugs[i:i+batch_size]
        results = pipeline.process_multiple_drugs(batch, targets)


DEBUGGING TIPS
==============

1. Enable verbose logging:
   import logging
   logging.basicConfig(level=logging.DEBUG)

2. Save intermediate results:
   result = pipeline.process_drug(..., save_intermediate=True)

3. Check LLM response quality:
   print(f"Description: {description.refined_description[:200]}")

4. Validate target predictions:
   for pred in result.predictions:
       if pred.confidence == TargetConfidence.VERY_HIGH:
           print(f"✓ {pred.target}")


"""

# ============================================================================
# 8. PERFORMANCE CONSIDERATIONS
# ============================================================================

"""
COMPUTATIONAL COMPLEXITY
==========================

Phase 1 (Description Generation):
  - PubMed API calls: 2 (search + fetch)
  - LLM calls: 2 (initial + refinement)
  - Bottleneck: LLM response time
  - Time per drug: 2-5 minutes

Phase 2 (Target Detection):
  - LLM calls: num_runs (5 recommended)
  - Aggregation: O(predictions * num_runs)
  - Bottleneck: Multiple LLM calls for self-consistency
  - Time per drug: 5-15 minutes (depending on num_runs)

Total: 10-20 minutes per drug

API COSTS (Example rates):
  - Claude 3 Opus: ~$15-30 per drug
  - GPT-4: ~$10-25 per drug
  - Batch processing: 30-40% savings


OPTIMIZATION STRATEGIES
========================

1. Parallel Processing:
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=4) as executor:
       results = list(executor.map(
           lambda d: pipeline.process_drug(d, targets),
           drugs
       ))

2. Caching:
   Cache drug descriptions to avoid re-fetching abstracts
   Cache few-shot examples to reuse across drugs

3. Prompt Engineering:
   Optimize prompt templates for faster LLM response
   Use shorter, more focused prompts

4. Batch API Calls:
   Use batch processing APIs where available
   Reduces per-call overhead


"""

# ============================================================================
# 9. INTEGRATION WITH EXISTING SYSTEMS
# ============================================================================

"""
INTEGRATION EXAMPLES
======================

Integration with Database:
  import sqlite3
  
  def save_to_db(result, db_path="drugs.db"):
      conn = sqlite3.connect(db_path)
      cursor = conn.cursor()
      
      cursor.execute('''
          INSERT INTO drug_targets (drug_name, target, confidence)
          VALUES (?, ?, ?)
      ''', (result['drug_name'], pred['target'], pred['confidence']))
      
      conn.commit()
      conn.close()

Integration with REST API:
  from fastapi import FastAPI
  
  app = FastAPI()
  
  @app.post("/predict-targets")
  async def predict_targets(drug_data: DrugMetadata):
      result = pipeline.process_drug(drug_data, available_targets)
      return result

Integration with Workflow Systems:
  # Nextflow or Snakemake integration
  rule detect_drug_targets:
      input:
          drug_info="drug_metadata.json"
      output:
          predictions="targets_{drug}.json"
      script:
          "scripts/run_pipeline.py"


"""

# ============================================================================
# 10. CITATION AND REFERENCES
# ============================================================================

"""
CITATION
=========

If you use this pipeline in your research, please cite:

Original Paper:
  [Reference to the original notebook/paper]

Related Work:
  - Few-shot learning for drug discovery
  - Self-consistency in LLM predictions
  - Drug-target interaction prediction


USEFUL RESOURCES
=================

- BioPython Entrez: https://biopython.org/wiki/Documentation
- STRING Database: https://string-db.org/
- PubMed API: https://www.ncbi.nlm.nih.gov/home/develop/api/
- Anthropic API: https://docs.anthropic.com/
- OpenAI API: https://platform.openai.com/docs/


"""

print(__doc__)
