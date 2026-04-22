"""
Module for fetching and processing drug-related abstracts from PubMed.
This module handles the data collection phase of the drug target detection pipeline.
"""

from Bio import Entrez
from typing import List, Optional
import warnings


class DrugAbstractFetcher:
    """Fetches PubMed abstracts for drugs using Entrez API."""
    
    def __init__(self, email: str):
        """
        Initialize the fetcher with Entrez email configuration.
        
        Args:
            email (str): Email address for Entrez API (required by NCBI)
        """
        Entrez.email = email
        
    def fetch_abstracts(
        self, 
        drug_name: str, 
        num_abstracts: int = 10
    ) -> List[str]:
        """
        Fetch PubMed abstracts for a given drug.
        
        Args:
            drug_name (str): Name of the drug to search
            num_abstracts (int): Number of abstracts to retrieve (default: 10)
            
        Returns:
            List[str]: List of abstract texts
        """
        try:
            # Step 1: Search for PubMed IDs
            handle = Entrez.esearch(
                db="pubmed", 
                term=drug_name, 
                retmax=num_abstracts, 
                sort="relevance"
            )
            search_results = Entrez.read(handle)
            handle.close()
            
            id_list = search_results.get("IdList", [])
            
            if not id_list:
                warnings.warn(f"No PubMed results found for drug: {drug_name}")
                return []
            
            # Step 2: Fetch details for each PubMed ID
            handle = Entrez.efetch(
                db="pubmed", 
                id=id_list, 
                rettype="xml"
            )
            papers = Entrez.read(handle)['PubmedArticle']
            handle.close()
            
            # Step 3: Parse abstracts
            abstracts = []
            for i, paper in enumerate(papers):
                try:
                    abstract_text = paper['MedlineCitation']['Article']['Abstract']['AbstractText'][0]
                    abstracts.append(abstract_text)
                except (KeyError, IndexError, TypeError):
                    # Some papers may not have abstracts
                    continue
            
            return abstracts
            
        except Exception as e:
            warnings.warn(f"Error fetching abstracts for {drug_name}: {str(e)}")
            return []
    
    def format_abstracts(self, abstracts: List[str]) -> str:
        """
        Format abstracts as a single string for LLM input.
        
        Args:
            abstracts (List[str]): List of abstract texts
            
        Returns:
            str: Formatted abstracts
        """
        formatted = []
        for i, abstract in enumerate(abstracts):
            formatted.append(f"Abstract {i+1}: {abstract}")
        return "\n\n".join(formatted)


class DrugMetadata:
    """Container for drug metadata."""
    
    def __init__(
        self,
        name: str,
        smiles: str,
        inchi_key: Optional[str] = None,
        moa: Optional[str] = None,
        targets: Optional[List[str]] = None
    ):
        """
        Initialize drug metadata.
        
        Args:
            name (str): Drug name
            smiles (str): SMILES notation
            inchi_key (str, optional): InChI Key
            moa (str, optional): Mechanism of action
            targets (List[str], optional): Known targets (if available)
        """
        self.name = name
        self.smiles = smiles
        self.inchi_key = inchi_key
        self.moa = moa
        self.targets = targets or []
    
    def to_dict(self):
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "smiles": self.smiles,
            "inchi_key": self.inchi_key,
            "moa": self.moa,
            "targets": self.targets
        }
    
    def __repr__(self):
        return f"DrugMetadata(name={self.name}, targets={self.targets})"
