"""
Pipeline 1: Drug Description Generation and Refinement
========================================================

This pipeline generates refined drug descriptions by:
1. Creating initial drug descriptions from metadata (name, MOA, targets)
2. Refining descriptions using PubMed abstracts
3. Returning comprehensive drug characterizations for downstream analysis
"""

from typing import Optional, Dict, List
import json
from dataclasses import dataclass, asdict
from drug_abstract_fetcher import DrugAbstractFetcher, DrugMetadata


@dataclass
class DrugDescription:
    """Container for generated drug descriptions."""
    drug_name: str
    initial_description: str
    refined_description: str
    abstracts: List[str]
    metadata: Dict
    
    def to_dict(self):
        return asdict(self)
    
    def save(self, filepath: str):
        """Save description to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str):
        """Load description from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)


class DrugDescriptionGenerator:
    """Generates initial drug descriptions from metadata."""
    
    def __init__(self, llm_client=None):
        """
        Initialize the generator.
        
        Args:
            llm_client: LLM client (e.g., Anthropic, OpenAI) for generating descriptions
        """
        self.llm = llm_client
    
    def generate_initial_description(
        self,
        drug_metadata: DrugMetadata
    ) -> str:
        """
        Generate initial drug description from metadata.
        
        This is the first LLM step that creates a basic understanding
        of the drug from its name, MOA, and targets.
        
        Args:
            drug_metadata (DrugMetadata): Drug metadata
            
        Returns:
            str: Initial drug description
        """
        prompt = f"""Based on the following drug information, provide a comprehensive description of its mechanism of action and biological effects:

Drug Name: {drug_metadata.name}
SMILES: {drug_metadata.smiles}
Mechanism of Action: {drug_metadata.moa or 'Unknown'}
Known Targets: {', '.join(drug_metadata.targets) if drug_metadata.targets else 'Unknown'}

Please provide a detailed description covering:
1. Primary mechanism of action
2. Molecular targets and interactions
3. Cellular effects
4. Potential therapeutic applications

Description:"""
        
        if self.llm is None:
            return self._mock_llm_call(prompt)
        
        return self._call_llm(prompt)
    
    def _call_llm(self, prompt: str) -> str:
        """Call actual LLM service."""
        # This should be implemented based on your LLM provider
        # Example for Anthropic API
        try:
            response = self.llm.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return self._mock_llm_call(prompt)
    
    def _mock_llm_call(self, prompt: str) -> str:
        """Mock LLM call for testing (returns placeholder)."""
        return "[Mock LLM Response] Initial drug description generated from metadata."


class DrugDescriptionRefiner:
    """Refines drug descriptions using PubMed abstracts."""
    
    def __init__(self, llm_client=None):
        """
        Initialize the refiner.
        
        Args:
            llm_client: LLM client for refining descriptions
        """
        self.llm = llm_client
    
    def refine_description(
        self,
        initial_description: str,
        abstracts: List[str],
        drug_name: str
    ) -> str:
        """
        Refine drug description using PubMed abstracts.
        
        This is the second LLM step that incorporates recent literature
        to create a more comprehensive and evidence-based description.
        
        Args:
            initial_description (str): Initial description from first LLM step
            abstracts (List[str]): PubMed abstracts
            drug_name (str): Drug name for context
            
        Returns:
            str: Refined drug description
        """
        formatted_abstracts = self._format_abstracts(abstracts)
        
        prompt = f"""You are a pharmacology expert. Please refine and expand the following drug description using the provided recent scientific literature.

Drug: {drug_name}

Initial Description:
{initial_description}

---

Recent Scientific Literature:
{formatted_abstracts}

---

Please provide a refined description that:
1. Incorporates findings from the recent literature
2. Updates any outdated information
3. Adds new mechanisms of action discovered in recent studies
4. Includes information about drug metabolism and effects on the tumor microenvironment
5. Maintains scientific accuracy while being comprehensive

Refined Description:"""
        
        if self.llm is None:
            return self._mock_llm_call(prompt)
        
        return self._call_llm(prompt)
    
    def _call_llm(self, prompt: str) -> str:
        """Call actual LLM service."""
        try:
            response = self.llm.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return self._mock_llm_call(prompt)
    
    def _mock_llm_call(self, prompt: str) -> str:
        """Mock LLM call for testing."""
        return "[Mock LLM Response] Refined drug description incorporating literature insights."
    
    @staticmethod
    def _format_abstracts(abstracts: List[str]) -> str:
        """Format abstracts for prompt inclusion."""
        formatted = []
        for i, abstract in enumerate(abstracts, 1):
            formatted.append(f"Abstract {i}: {abstract}")
        return "\n\n".join(formatted)


class DescriptionGenerationPipeline:
    """Main pipeline for drug description generation and refinement."""
    
    def __init__(
        self,
        email: str,
        llm_client=None
    ):
        """
        Initialize the pipeline.
        
        Args:
            email (str): Email for Entrez API
            llm_client: LLM client for generation and refinement
        """
        self.abstract_fetcher = DrugAbstractFetcher(email)
        self.generator = DrugDescriptionGenerator(llm_client)
        self.refiner = DrugDescriptionRefiner(llm_client)
    
    def run(
        self,
        drug_metadata: DrugMetadata,
        num_abstracts: int = 10
    ) -> DrugDescription:
        """
        Run the complete description generation pipeline.
        
        Args:
            drug_metadata (DrugMetadata): Drug metadata
            num_abstracts (int): Number of abstracts to fetch
            
        Returns:
            DrugDescription: Generated and refined drug description
        """
        print(f"Starting description pipeline for {drug_metadata.name}...")
        
        # Step 1: Fetch abstracts
        print(f"Fetching abstracts from PubMed...")
        abstracts = self.abstract_fetcher.fetch_abstracts(
            drug_metadata.name,
            num_abstracts=num_abstracts
        )
        print(f"Retrieved {len(abstracts)} abstracts")
        
        # Step 2: Generate initial description
        print(f"Generating initial description...")
        initial_description = self.generator.generate_initial_description(
            drug_metadata
        )
        
        # Step 3: Refine description with abstracts
        print(f"Refining description with literature insights...")
        refined_description = self.refiner.refine_description(
            initial_description,
            abstracts,
            drug_metadata.name
        )
        
        # Step 4: Package results
        result = DrugDescription(
            drug_name=drug_metadata.name,
            initial_description=initial_description,
            refined_description=refined_description,
            abstracts=abstracts,
            metadata=drug_metadata.to_dict()
        )
        
        print(f"Description pipeline complete for {drug_metadata.name}")
        return result


# Example usage
if __name__ == "__main__":
    # Example: Create pipeline and generate description for a drug
    from drug_abstract_fetcher import DrugMetadata
    
    # Create drug metadata
    docetaxel = DrugMetadata(
        name="Docetaxel",
        smiles="CC1=C2[C@H](C(=O)[C@@]3([C@H](C[C@@H]4[C@]([C@...",
        moa="Microtubule stabilisation",
        targets=["TUBB", "TUBA"]
    )
    
    # Initialize pipeline (without actual LLM for this example)
    pipeline = DescriptionGenerationPipeline(
        email="your_email@example.com",
        llm_client=None
    )
    
    # Run pipeline
    description = pipeline.run(docetaxel, num_abstracts=5)
    
    print("\n=== Generated Description ===")
    print(f"Drug: {description.drug_name}")
    print(f"\nInitial Description:\n{description.initial_description[:200]}...")
    print(f"\nRefined Description:\n{description.refined_description[:200]}...")
    
    # Save to file
    # description.save("docetaxel_description.json")
