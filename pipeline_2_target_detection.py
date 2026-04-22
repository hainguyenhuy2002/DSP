"""
Pipeline 2: Target Detection using Few-Shot Learning with Self-Consistency
===========================================================================

This pipeline detects drug targets by:
1. Using few-shot learning with examples of known drugs and their targets
2. Running the prediction K times for self-consistency
3. Aggregating results to find the most confident target predictions
4. Providing rationales for each predicted target
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
from enum import Enum


class TargetConfidence(Enum):
    """Confidence levels for target predictions."""
    VERY_HIGH = "very_high"  # Appears in 5/5 or 4/5 runs
    HIGH = "high"            # Appears in 3/5 runs
    MEDIUM = "medium"        # Appears in 2/5 runs
    LOW = "low"              # Appears in 1/5 run


@dataclass
class TargetPrediction:
    """Container for a single target prediction."""
    target: str
    confidence: TargetConfidence
    count: int
    rationales: List[str]
    metadata: Dict = None
    
    def to_dict(self):
        return {
            "target": self.target,
            "confidence": self.confidence.value,
            "count": self.count,
            "rationales": self.rationales,
            "metadata": self.metadata or {}
        }


@dataclass
class TargetDetectionResult:
    """Container for complete target detection results."""
    drug_name: str
    drug_description: str
    predictions: List[TargetPrediction]
    num_runs: int
    available_targets: List[str]
    
    def to_dict(self):
        return {
            "drug_name": self.drug_name,
            "drug_description": self.drug_description[:500],  # Truncate for storage
            "predictions": [p.to_dict() for p in self.predictions],
            "num_runs": self.num_runs,
            "available_targets": self.available_targets
        }
    
    def save(self, filepath: str):
        """Save results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def get_high_confidence_targets(self) -> List[str]:
        """Get only high and very high confidence targets."""
        return [
            p.target for p in self.predictions 
            if p.confidence in [TargetConfidence.VERY_HIGH, TargetConfidence.HIGH]
        ]


class FewShotExampleBank:
    """Repository of drug-target examples for few-shot learning."""
    
    def __init__(self):
        """Initialize the example bank."""
        self.examples: List[Dict] = []
    
    def add_example(
        self,
        drug_name: str,
        drug_description: str,
        targets: List[str],
        rationale: Optional[str] = None
    ):
        """
        Add a drug-target example to the bank.
        
        Args:
            drug_name (str): Name of the drug
            drug_description (str): Description of the drug
            targets (List[str]): Known targets
            rationale (str, optional): Explanation of why these are targets
        """
        self.examples.append({
            "drug_name": drug_name,
            "drug_description": drug_description,
            "targets": targets,
            "rationale": rationale or f"Known targets for {drug_name}"
        })
    
    def get_examples(self, num_examples: int = 3) -> List[Dict]:
        """
        Get a subset of examples for few-shot learning.
        
        Args:
            num_examples (int): Number of examples to retrieve
            
        Returns:
            List[Dict]: Selected examples
        """
        return self.examples[:num_examples]
    
    def format_for_prompt(self, num_examples: int = 3) -> str:
        """
        Format examples for inclusion in LLM prompt.
        
        Args:
            num_examples (int): Number of examples to include
            
        Returns:
            str: Formatted examples
        """
        examples = self.get_examples(num_examples)
        formatted = []
        
        for i, example in enumerate(examples, 1):
            formatted.append(
                f"Example {i}:\n"
                f"Drug: {example['drug_name']}\n"
                f"Description: {example['drug_description'][:200]}...\n"
                f"Targets: {', '.join(example['targets'])}\n"
                f"Rationale: {example['rationale']}\n"
            )
        
        return "\n".join(formatted)
    
    def save(self, filepath: str):
        """Save examples to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.examples, f, indent=2)
    
    @classmethod
    def load(cls, filepath: str):
        """Load examples from JSON file."""
        bank = cls()
        with open(filepath, 'r') as f:
            bank.examples = json.load(f)
        return bank


class TargetDetector:
    """Detects drug targets using few-shot learning."""
    
    def __init__(
        self,
        llm_client=None,
        example_bank: Optional[FewShotExampleBank] = None
    ):
        """
        Initialize the detector.
        
        Args:
            llm_client: LLM client for prediction
            example_bank (FewShotExampleBank, optional): Bank of examples for few-shot learning
        """
        self.llm = llm_client
        self.example_bank = example_bank or FewShotExampleBank()
    
    def predict_targets(
        self,
        drug_description: str,
        drug_name: str,
        available_targets: List[str],
        num_predictions: int = 5
    ) -> List[Tuple[str, str]]:
        """
        Predict drug targets in a single run.
        
        Args:
            drug_description (str): Refined drug description
            drug_name (str): Drug name
            available_targets (List[str]): List of all available target proteins
            num_predictions (int): Number of targets to predict (default: 5)
            
        Returns:
            List[Tuple[str, str]]: List of (target, rationale) tuples
        """
        prompt = self._build_prediction_prompt(
            drug_description,
            drug_name,
            available_targets,
            num_predictions
        )
        
        if self.llm is None:
            return self._mock_llm_prediction(num_predictions, available_targets)
        
        response = self._call_llm(prompt)
        return self._parse_predictions(response)
    
    def _build_prediction_prompt(
        self,
        drug_description: str,
        drug_name: str,
        available_targets: List[str],
        num_predictions: int
    ) -> str:
        """Build the few-shot learning prompt."""
        few_shot_examples = self.example_bank.format_for_prompt(num_examples=3)
        targets_list = ", ".join(available_targets)
        
        prompt = f"""You are an expert in pharmacology and drug mechanism of action. Your task is to predict the protein targets for a given drug.

=== FEW-SHOT EXAMPLES ===

{few_shot_examples}

=== TASK ===

Based on the drug description and the few-shot examples above, predict the {num_predictions} most likely targets for:

Drug: {drug_name}
Description: {drug_description}

Available targets to choose from:
{targets_list}

For each predicted target, provide:
1. Target name (must be from the available targets list)
2. Rationale explaining why this is a likely target

Important:
- Only select targets from the provided list
- Do not repeat targets
- Order predictions by confidence (highest first)
- Be specific about molecular interactions

Predictions:"""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM."""
        try:
            response = self.llm.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return self._mock_llm_call()
    
    def _mock_llm_call(self) -> str:
        """Mock LLM response for testing."""
        return """Target 1: TARGET_A
Rationale: Inhibits microtubule assembly.

Target 2: TARGET_B
Rationale: Involved in cell cycle regulation.

Target 3: TARGET_C
Rationale: Promotes apoptosis through caspase activation."""
    
    def _mock_llm_prediction(
        self,
        num_predictions: int,
        available_targets: List[str]
    ) -> List[Tuple[str, str]]:
        """Generate mock predictions."""
        predictions = []
        for i in range(min(num_predictions, len(available_targets))):
            target = available_targets[i]
            rationale = f"Mock rationale for {target}"
            predictions.append((target, rationale))
        return predictions
    
    @staticmethod
    def _parse_predictions(response: str) -> List[Tuple[str, str]]:
        """
        Parse LLM response to extract target predictions.
        
        Expected format:
        Target 1: TARGET_NAME
        Rationale: explanation...
        
        Args:
            response (str): LLM response text
            
        Returns:
            List[Tuple[str, str]]: List of (target, rationale) tuples
        """
        predictions = []
        lines = response.strip().split('\n')
        
        current_target = None
        current_rationale = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Target'):
                if current_target and current_rationale:
                    predictions.append((current_target, current_rationale))
                
                # Extract target name
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_target = parts[1].strip()
            
            elif line.startswith('Rationale'):
                # Extract rationale
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_rationale = parts[1].strip()
        
        # Don't forget the last one
        if current_target and current_rationale:
            predictions.append((current_target, current_rationale))
        
        return predictions


class SelfConsistencyAggregator:
    """Aggregates target predictions across multiple runs."""
    
    @staticmethod
    def aggregate(
        predictions_list: List[List[Tuple[str, str]]],
        num_runs: int
    ) -> Dict[str, Dict]:
        """
        Aggregate predictions from multiple runs.
        
        Args:
            predictions_list (List[List[Tuple[str, str]]]): Predictions from K runs
            num_runs (int): Number of runs performed
            
        Returns:
            Dict[str, Dict]: Aggregated predictions with counts and rationales
        """
        aggregated = defaultdict(lambda: {
            'count': 0,
            'rationales': []
        })
        
        for run_predictions in predictions_list:
            for target, rationale in run_predictions:
                aggregated[target]['count'] += 1
                if rationale not in aggregated[target]['rationales']:
                    aggregated[target]['rationales'].append(rationale)
        
        return dict(aggregated)
    
    @staticmethod
    def get_confidence_level(count: int, num_runs: int) -> TargetConfidence:
        """
        Determine confidence level based on appearance count.
        
        Args:
            count (int): Number of runs in which target appeared
            num_runs (int): Total number of runs
            
        Returns:
            TargetConfidence: Confidence level
        """
        ratio = count / num_runs
        
        if ratio >= 0.8:  # 4/5 or 5/5
            return TargetConfidence.VERY_HIGH
        elif ratio >= 0.6:  # 3/5
            return TargetConfidence.HIGH
        elif ratio >= 0.4:  # 2/5
            return TargetConfidence.MEDIUM
        else:
            return TargetConfidence.LOW


class TargetDetectionPipeline:
    """Main pipeline for target detection with self-consistency."""
    
    def __init__(
        self,
        llm_client=None,
        example_bank: Optional[FewShotExampleBank] = None
    ):
        """
        Initialize the pipeline.
        
        Args:
            llm_client: LLM client
            example_bank (FewShotExampleBank, optional): Examples for few-shot learning
        """
        self.detector = TargetDetector(llm_client, example_bank)
        self.aggregator = SelfConsistencyAggregator()
    
    def run(
        self,
        drug_name: str,
        drug_description: str,
        available_targets: List[str],
        num_runs: int = 5,
        num_predictions_per_run: int = 5
    ) -> TargetDetectionResult:
        """
        Run the target detection pipeline with self-consistency.
        
        Args:
            drug_name (str): Name of the drug
            drug_description (str): Refined drug description
            available_targets (List[str]): List of all available target proteins
            num_runs (int): Number of prediction runs (default: 5)
            num_predictions_per_run (int): Targets to predict per run (default: 5)
            
        Returns:
            TargetDetectionResult: Aggregated results
        """
        print(f"Starting target detection for {drug_name}...")
        print(f"Running {num_runs} independent predictions with self-consistency...")
        
        # Run predictions K times
        all_predictions = []
        for run in range(num_runs):
            print(f"  Run {run + 1}/{num_runs}...", end=' ', flush=True)
            predictions = self.detector.predict_targets(
                drug_description,
                drug_name,
                available_targets,
                num_predictions_per_run
            )
            all_predictions.append(predictions)
            print("✓")
        
        # Aggregate predictions
        print(f"Aggregating results across {num_runs} runs...")
        aggregated = self.aggregator.aggregate(all_predictions, num_runs)
        
        # Convert to TargetPrediction objects
        target_predictions = []
        for target, data in sorted(
            aggregated.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        ):
            confidence = self.aggregator.get_confidence_level(
                data['count'],
                num_runs
            )
            
            prediction = TargetPrediction(
                target=target,
                confidence=confidence,
                count=data['count'],
                rationales=data['rationales'],
                metadata={'num_runs': num_runs}
            )
            target_predictions.append(prediction)
        
        result = TargetDetectionResult(
            drug_name=drug_name,
            drug_description=drug_description,
            predictions=target_predictions,
            num_runs=num_runs,
            available_targets=available_targets
        )
        
        print(f"Target detection complete!")
        return result


# Example usage
if __name__ == "__main__":
    # Create example bank with sample drugs
    example_bank = FewShotExampleBank()
    
    example_bank.add_example(
        drug_name="Docetaxel",
        drug_description="A microtubule-stabilizing agent that prevents...",
        targets=["TUBB", "TUBA1A", "TUBA1B"],
        rationale="Binds to β-tubulin and stabilizes microtubules"
    )
    
    example_bank.add_example(
        drug_name="Paclitaxel",
        drug_description="Similar to docetaxel, promotes microtubule...",
        targets=["TUBB", "TUBA1A"],
        rationale="Stabilizes microtubules through tubulin binding"
    )
    
    example_bank.add_example(
        drug_name="Doxorubicin",
        drug_description="Topoisomerase II inhibitor that intercalates...",
        targets=["TOP2A", "TOP2B"],
        rationale="Intercalates DNA and inhibits topoisomerase II"
    )
    
    # Initialize pipeline
    pipeline = TargetDetectionPipeline(
        llm_client=None,
        example_bank=example_bank
    )
    
    # Example available targets (proteins)
    available_targets = [
        "TUBB", "TUBA1A", "TUBA1B", "TOP2A", "TOP2B",
        "CDKN1A", "TP53", "BAX", "BCL2", "MAPK1",
        "ESR1", "AR", "EGFR", "HER2", "ALK"
    ]
    
    # Run target detection
    result = pipeline.run(
        drug_name="Test_Drug",
        drug_description="A novel inhibitor with effects on cell cycle...",
        available_targets=available_targets,
        num_runs=5,
        num_predictions_per_run=5
    )
    
    # Display results
    print("\n=== TARGET DETECTION RESULTS ===")
    print(f"Drug: {result.drug_name}")
    print(f"Number of predictions: {len(result.predictions)}")
    print(f"\nHigh Confidence Targets: {result.get_high_confidence_targets()}")
    
    for pred in result.predictions[:3]:
        print(f"\nTarget: {pred.target}")
        print(f"Confidence: {pred.confidence.value}")
        print(f"Appeared in {pred.count}/{result.num_runs} runs")
        print(f"Rationales: {pred.rationales[0] if pred.rationales else 'N/A'}")
    
    # Save results
    # result.save("target_predictions.json")
