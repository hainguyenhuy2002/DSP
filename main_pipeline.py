"""
Main Integration Script for Drug Target Detection
==================================================

This script demonstrates how to use both pipelines together:
1. Pipeline 1: Generate refined drug descriptions
2. Pipeline 2: Detect drug targets using few-shot learning

The workflow follows the figure provided:
Drug Metadata → PubMed Abstracts → LLM Description → Few-Shot Learning → Target Prediction
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

from drug_abstract_fetcher import DrugAbstractFetcher, DrugMetadata
from pipeline_1_description_generation import (
    DescriptionGenerationPipeline,
    DrugDescription
)
from pipeline_2_target_detection import (
    TargetDetectionPipeline,
    FewShotExampleBank,
    TargetDetectionResult
)


class CompleteTargetDetectionPipeline:
    """
    Complete drug target detection pipeline combining both description
    generation and target prediction with self-consistency.
    """
    
    def __init__(
        self,
        email: str,
        llm_client=None,
        output_dir: str = "./results"
    ):
        """
        Initialize the complete pipeline.
        
        Args:
            email (str): Email for Entrez API
            llm_client: LLM client (e.g., Anthropic/OpenAI)
            output_dir (str): Directory for saving results
        """
        self.email = email
        self.llm_client = llm_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize pipelines
        self.description_pipeline = DescriptionGenerationPipeline(
            email=email,
            llm_client=llm_client
        )
        
        self.example_bank = FewShotExampleBank()
        self.target_pipeline = TargetDetectionPipeline(
            llm_client=llm_client,
            example_bank=self.example_bank
        )
    
    def add_few_shot_example(
        self,
        drug_name: str,
        drug_description: str,
        targets: List[str],
        rationale: Optional[str] = None
    ):
        """
        Add a drug example for few-shot learning.
        
        Args:
            drug_name (str): Drug name
            drug_description (str): Drug description
            targets (List[str]): Known targets
            rationale (str, optional): Explanation of targets
        """
        self.example_bank.add_example(
            drug_name=drug_name,
            drug_description=drug_description,
            targets=targets,
            rationale=rationale
        )
    
    def process_drug(
        self,
        drug_metadata: DrugMetadata,
        available_targets: List[str],
        num_abstracts: int = 10,
        num_target_runs: int = 5,
        num_predictions_per_run: int = 5,
        save_intermediate: bool = True
    ) -> Dict:
        """
        Process a single drug through the complete pipeline.
        
        Args:
            drug_metadata (DrugMetadata): Drug metadata
            available_targets (List[str]): List of all available targets
            num_abstracts (int): Number of PubMed abstracts to fetch
            num_target_runs (int): Number of target prediction runs
            num_predictions_per_run (int): Targets to predict per run
            save_intermediate (bool): Save intermediate results
            
        Returns:
            Dict: Complete results including descriptions and target predictions
        """
        print(f"\n{'='*70}")
        print(f"PROCESSING DRUG: {drug_metadata.name}")
        print(f"{'='*70}")
        
        # ===== PHASE 1: DESCRIPTION GENERATION =====
        print(f"\nPHASE 1: DRUG DESCRIPTION GENERATION")
        print(f"{'-'*70}")
        
        drug_description = self.description_pipeline.run(
            drug_metadata=drug_metadata,
            num_abstracts=num_abstracts
        )
        
        if save_intermediate:
            desc_file = self.output_dir / f"{drug_metadata.name}_description.json"
            drug_description.save(str(desc_file))
            print(f"Description saved to: {desc_file}")
        
        # ===== PHASE 2: TARGET DETECTION =====
        print(f"\nPHASE 2: TARGET DETECTION WITH SELF-CONSISTENCY")
        print(f"{'-'*70}")
        
        target_results = self.target_pipeline.run(
            drug_name=drug_metadata.name,
            drug_description=drug_description.refined_description,
            available_targets=available_targets,
            num_runs=num_target_runs,
            num_predictions_per_run=num_predictions_per_run
        )
        
        if save_intermediate:
            results_file = self.output_dir / f"{drug_metadata.name}_target_predictions.json"
            target_results.save(str(results_file))
            print(f"Target predictions saved to: {results_file}")
        
        # ===== COMPILE RESULTS =====
        complete_results = {
            "drug_name": drug_metadata.name,
            "metadata": drug_metadata.to_dict(),
            "description": drug_description.to_dict(),
            "target_detection": target_results.to_dict(),
            "high_confidence_targets": target_results.get_high_confidence_targets()
        }
        
        return complete_results
    
    def process_multiple_drugs(
        self,
        drugs: List[DrugMetadata],
        available_targets: List[str],
        **kwargs
    ) -> List[Dict]:
        """
        Process multiple drugs through the pipeline.
        
        Args:
            drugs (List[DrugMetadata]): List of drugs to process
            available_targets (List[str]): List of all available targets
            **kwargs: Additional arguments passed to process_drug
            
        Returns:
            List[Dict]: Results for all drugs
        """
        results = []
        
        for i, drug in enumerate(drugs, 1):
            print(f"\n\nDrug {i}/{len(drugs)}")
            result = self.process_drug(
                drug_metadata=drug,
                available_targets=available_targets,
                **kwargs
            )
            results.append(result)
        
        return results
    
    def save_summary(self, results: List[Dict], filename: str = "summary.json"):
        """
        Save a summary of all results.
        
        Args:
            results (List[Dict]): Results from all processed drugs
            filename (str): Output filename
        """
        summary = {
            "num_drugs": len(results),
            "drugs": [
                {
                    "name": r["drug_name"],
                    "targets": r["high_confidence_targets"],
                    "num_predictions": len(r["target_detection"]["predictions"])
                }
                for r in results
            ]
        }
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nSummary saved to: {filepath}")


def create_example_target_list() -> List[str]:
    """
    Create a realistic list of available protein targets.
    This simulates the "List of Active Proteins from STRING with Cells" from the figure.
    """
    return [
        # Cell cycle proteins
        "TUBB", "TUBA1A", "TUBA1B", "CDK1", "CDK2", "CCNB1", "CCNB2",
        
        # Apoptosis related
        "TP53", "BAX", "BCL2", "CASP3", "CASP8", "CASP9", "PMAIP1", "BBC3",
        
        # DNA damage/replication
        "TOP2A", "TOP2B", "POLD1", "POLE", "RAD51", "BRCA1", "BRCA2",
        
        # Growth signaling
        "EGFR", "HER2", "ALK", "ROS1", "BRAF", "KRAS", "PIK3CA", "PTEN",
        
        # Kinase signaling
        "MAPK1", "MAPK3", "AKT1", "AKT2", "mTOR", "GSK3B",
        
        # Hormone receptors
        "ESR1", "ESR2", "AR", "PGR",
        
        # Immune related
        "CD8A", "CD4", "GZMA", "GZMB", "PRF1", "ICAM1",
        
        # Metabolism
        "LDHA", "PKM", "GLUT1", "HIF1A",
        
        # Angiogenesis
        "VEGFA", "VEGFR1", "VEGFR2", "PDGFRA", "PDGFRB",
        
        # Extracellular matrix
        "MMP2", "MMP9", "COL1A1", "FN1",
        
        # Other important targets
        "TNF", "IFNG", "IL2", "IL6", "IL10", "STAT3", "NF-kB"
    ]


def create_few_shot_examples() -> FewShotExampleBank:
    """
    Create a bank of example drugs for few-shot learning.
    These serve as training examples for the LLM.
    """
    bank = FewShotExampleBank()
    
    # Example 1: Docetaxel (from the notebook)
    bank.add_example(
        drug_name="Docetaxel",
        drug_description=(
            "Docetaxel is a semi-synthetic derivative of paclitaxel that acts as a "
            "microtubule-stabilizing agent. It binds to β-tubulin and prevents microtubule "
            "disassembly during mitosis, leading to cell cycle arrest at the G2/M phase and "
            "apoptosis. Additionally, it has immunomodulatory effects and activates the "
            "cGAS/STING pathway in certain cancer cells."
        ),
        targets=["TUBB", "TUBA1A", "TUBA1B"],
        rationale="Directly binds and stabilizes tubulin heterodimers"
    )
    
    # Example 2: Doxorubicin
    bank.add_example(
        drug_name="Doxorubicin",
        drug_description=(
            "Doxorubicin is a topoisomerase II inhibitor that intercalates into DNA. "
            "It prevents the re-ligation of DNA strands after topoisomerase II-mediated "
            "strand breaks, leading to accumulation of double-strand breaks and cell death. "
            "Also generates reactive oxygen species contributing to cell toxicity."
        ),
        targets=["TOP2A", "TOP2B"],
        rationale="Inhibits topoisomerase II-mediated DNA re-ligation"
    )
    
    # Example 3: Erlotinib
    bank.add_example(
        drug_name="Erlotinib",
        drug_description=(
            "Erlotinib is a selective inhibitor of epidermal growth factor receptor (EGFR) "
            "tyrosine kinase. It competitively binds to the ATP-binding site of EGFR kinase domain, "
            "preventing autophosphorylation and downstream signaling. Used for EGFR-mutant cancers."
        ),
        targets=["EGFR"],
        rationale="Competitive kinase inhibitor of EGFR ATP binding site"
    )
    
    return bank


def main_example():
    """
    Demonstrate the complete pipeline with example data.
    """
    print("="*70)
    print("DRUG TARGET DETECTION PIPELINE DEMONSTRATION")
    print("="*70)
    
    # Initialize the complete pipeline
    pipeline = CompleteTargetDetectionPipeline(
        email="your_email@example.com",  # Required for PubMed
        llm_client=None,  # Use actual LLM client in production
        output_dir="./drug_target_results"
    )
    
    # Add few-shot examples
    print("\nAdding few-shot learning examples...")
    example_bank = create_few_shot_examples()
    for example in example_bank.get_examples(num_examples=3):
        pipeline.add_few_shot_example(
            drug_name=example['drug_name'],
            drug_description=example['drug_description'],
            targets=example['targets'],
            rationale=example['rationale']
        )
    print(f"✓ Added {len(example_bank.examples)} examples")
    
    # Get available targets
    available_targets = create_example_target_list()
    print(f"✓ Loaded {len(available_targets)} available protein targets")
    
    # Create example drugs to process
    example_drugs = [
        DrugMetadata(
            name="Docetaxel",
            smiles="CC1=C2[C@H](C(=O)[C@@]3([C@H](C[C@@H]4[C@]...",
            moa="Microtubule stabilisation",
            targets=["TUBB"]
        ),
        DrugMetadata(
            name="Cisplatin",
            smiles="N.N.Cl[Pt]Cl",
            moa="DNA crosslinker",
            targets=["DNA"]
        ),
    ]
    
    # Process drugs
    print(f"\nProcessing {len(example_drugs)} drug(s)...\n")
    results = pipeline.process_multiple_drugs(
        drugs=example_drugs,
        available_targets=available_targets,
        num_abstracts=5,
        num_target_runs=3,  # Reduced for demo
        num_predictions_per_run=5
    )
    
    # Save summary
    pipeline.save_summary(results)
    
    # Print final results
    print(f"\n{'='*70}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*70}")
    
    for result in results:
        print(f"\nDrug: {result['drug_name']}")
        print(f"High Confidence Targets: {result['high_confidence_targets']}")
        print(f"Total Predictions: {len(result['target_detection']['predictions'])}")
        
        # Show top 3 predictions
        print("Top 3 Predictions:")
        for pred in result['target_detection']['predictions'][:3]:
            print(f"  - {pred['target']} ({pred['confidence']}) - {pred['count']} appearances")


if __name__ == "__main__":
    main_example()
