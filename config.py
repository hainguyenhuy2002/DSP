"""
Configuration Template for Drug Target Detection Pipeline
=========================================================

This file contains configurable parameters and defaults for the pipeline.
Copy and modify this file to customize behavior for your use case.

Usage:
    from config import PipelineConfig
    config = PipelineConfig()
    # Modify as needed
    # pipeline = CompleteTargetDetectionPipeline(**config.to_dict())
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    MOCK = "mock"


@dataclass
class AbstractFetcherConfig:
    """Configuration for abstract fetching."""
    
    # Number of abstracts to fetch from PubMed
    num_abstracts: int = 10
    
    # Maximum number of retries for API calls
    max_retries: int = 3
    
    # Timeout for API calls (seconds)
    timeout: int = 30
    
    # Sort order for PubMed results
    sort_order: str = "relevance"  # or "recent"
    
    # Minimum abstract length (words)
    min_abstract_length: int = 50


@dataclass
class DescriptionGenerationConfig:
    """Configuration for Phase 1 (Description Generation)."""
    
    # Maximum tokens for initial description
    max_tokens_initial: int = 1000
    
    # Maximum tokens for refined description
    max_tokens_refined: int = 2000
    
    # Temperature for generation (0.0 to 2.0)
    # Lower = more deterministic, Higher = more creative
    temperature: float = 0.7
    
    # Whether to include SMILES in prompt
    include_smiles: bool = True
    
    # Whether to include known targets in prompt
    include_known_targets: bool = True
    
    # Whether to fetch abstracts if none available
    fetch_abstracts_if_empty: bool = True


@dataclass
class TargetDetectionConfig:
    """Configuration for Phase 2 (Target Detection)."""
    
    # Number of independent prediction runs (self-consistency)
    num_runs: int = 5
    
    # Number of targets to predict per run
    num_predictions_per_run: int = 5
    
    # Number of few-shot examples to include
    num_few_shot_examples: int = 3
    
    # Temperature for target prediction
    temperature: float = 0.7
    
    # Maximum tokens for prediction
    max_tokens: int = 1500
    
    # Minimum confidence to include (0.0 to 1.0)
    # 0.8 = VERY_HIGH, 0.6 = HIGH, 0.4 = MEDIUM, 0.2 = LOW
    min_confidence: float = 0.2
    
    # Sort predictions by confidence
    sort_by_confidence: bool = True
    
    # Include rationales in output
    include_rationales: bool = True


@dataclass
class LLMConfig:
    """Configuration for LLM interactions."""
    
    # LLM Provider to use
    provider: LLMProvider = LLMProvider.ANTHROPIC
    
    # Model name for Anthropic
    anthropic_model: str = "claude-opus-4-20250514"
    
    # Model name for OpenAI
    openai_model: str = "gpt-4"
    
    # API key (preferably from environment variable)
    api_key: Optional[str] = None
    
    # API endpoint (if custom)
    endpoint: Optional[str] = None
    
    # Timeout for API calls
    timeout: int = 60
    
    # Max retries on failure
    max_retries: int = 3
    
    # Retry delay (seconds)
    retry_delay: float = 1.0


@dataclass
class OutputConfig:
    """Configuration for output and saving."""
    
    # Output directory path
    output_dir: str = "./drug_target_results"
    
    # Save intermediate results
    save_intermediate: bool = True
    
    # Save descriptions to JSON
    save_descriptions: bool = True
    
    # Save target predictions to JSON
    save_predictions: bool = True
    
    # Save summary report
    save_summary: bool = True
    
    # Format for output files (json, csv, both)
    output_format: str = "json"
    
    # Whether to create timestamped subdirectories
    use_timestamps: bool = True
    
    # Pretty print JSON
    pretty_print_json: bool = True


@dataclass
class ValidationConfig:
    """Configuration for validation and checking."""
    
    # Validate drug metadata completeness
    validate_metadata: bool = True
    
    # Check if targets exist in available list
    validate_targets_exist: bool = True
    
    # Check abstract count (warn if too low)
    min_abstracts_warning: int = 3
    
    # Check prediction diversity
    check_prediction_diversity: bool = True
    
    # Warn if all predictions are same target
    warn_low_diversity: bool = True


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    
    # Email for Entrez API (REQUIRED)
    email: str = "user@example.com"
    
    # Sub-configurations
    abstract_fetcher: AbstractFetcherConfig = None
    description_generation: DescriptionGenerationConfig = None
    target_detection: TargetDetectionConfig = None
    llm: LLMConfig = None
    output: OutputConfig = None
    validation: ValidationConfig = None
    
    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    verbose: bool = False
    
    def __post_init__(self):
        """Initialize default sub-configs."""
        if self.abstract_fetcher is None:
            self.abstract_fetcher = AbstractFetcherConfig()
        if self.description_generation is None:
            self.description_generation = DescriptionGenerationConfig()
        if self.target_detection is None:
            self.target_detection = TargetDetectionConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.validation is None:
            self.validation = ValidationConfig()
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            'email': self.email,
            'abstract_fetcher': self.abstract_fetcher.__dict__,
            'description_generation': self.description_generation.__dict__,
            'target_detection': self.target_detection.__dict__,
            'llm': self.llm.__dict__,
            'output': self.output.__dict__,
            'validation': self.validation.__dict__,
            'log_level': self.log_level,
            'verbose': self.verbose
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'PipelineConfig':
        """Create config from dictionary."""
        return cls(
            email=config_dict.get('email', 'user@example.com'),
            abstract_fetcher=AbstractFetcherConfig(
                **config_dict.get('abstract_fetcher', {})
            ),
            description_generation=DescriptionGenerationConfig(
                **config_dict.get('description_generation', {})
            ),
            target_detection=TargetDetectionConfig(
                **config_dict.get('target_detection', {})
            ),
            llm=LLMConfig(**config_dict.get('llm', {})),
            output=OutputConfig(**config_dict.get('output', {})),
            validation=ValidationConfig(**config_dict.get('validation', {})),
            log_level=config_dict.get('log_level', 'INFO'),
            verbose=config_dict.get('verbose', False)
        )


# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

class PresetConfigs:
    """Pre-configured setups for different use cases."""
    
    @staticmethod
    def fast() -> PipelineConfig:
        """Fast mode - minimal accuracy, maximum speed."""
        config = PipelineConfig()
        config.abstract_fetcher.num_abstracts = 3
        config.target_detection.num_runs = 2
        config.target_detection.num_predictions_per_run = 3
        config.target_detection.num_few_shot_examples = 1
        return config
    
    @staticmethod
    def balanced() -> PipelineConfig:
        """Balanced mode - good accuracy and speed."""
        config = PipelineConfig()
        config.abstract_fetcher.num_abstracts = 10
        config.target_detection.num_runs = 5
        config.target_detection.num_predictions_per_run = 5
        config.target_detection.num_few_shot_examples = 3
        return config
    
    @staticmethod
    def accurate() -> PipelineConfig:
        """Accurate mode - maximum accuracy, longer runtime."""
        config = PipelineConfig()
        config.abstract_fetcher.num_abstracts = 15
        config.target_detection.num_runs = 10
        config.target_detection.num_predictions_per_run = 7
        config.target_detection.num_few_shot_examples = 5
        config.target_detection.min_confidence = 0.4
        return config
    
    @staticmethod
    def research() -> PipelineConfig:
        """Research mode - comprehensive analysis."""
        config = PipelineConfig()
        config.abstract_fetcher.num_abstracts = 20
        config.target_detection.num_runs = 15
        config.target_detection.num_predictions_per_run = 10
        config.target_detection.num_few_shot_examples = 5
        config.output.save_intermediate = True
        config.verbose = True
        return config
    
    @staticmethod
    def demo() -> PipelineConfig:
        """Demo mode - for testing without API calls."""
        config = PipelineConfig()
        config.llm.provider = LLMProvider.MOCK
        config.abstract_fetcher.num_abstracts = 3
        config.target_detection.num_runs = 2
        return config


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Demonstrate how to use the configuration."""
    
    # Option 1: Use default config
    config = PipelineConfig(email="user@example.com")
    
    # Option 2: Use a preset
    config = PresetConfigs.balanced()
    config.email = "user@example.com"
    
    # Option 3: Customize specific settings
    config = PipelineConfig(email="user@example.com")
    config.target_detection.num_runs = 10
    config.target_detection.temperature = 0.5
    config.output.output_dir = "./my_results"
    
    # Option 4: Load from dictionary
    config_dict = {
        'email': 'user@example.com',
        'target_detection': {'num_runs': 7},
        'llm': {'provider': LLMProvider.OPENAI.value}
    }
    config = PipelineConfig.from_dict(config_dict)
    
    return config


if __name__ == "__main__":
    # Display available presets
    print("="*70)
    print("AVAILABLE PRESET CONFIGURATIONS")
    print("="*70)
    
    print("\n1. FAST MODE (2-3 min per drug)")
    print("-" * 70)
    fast_config = PresetConfigs.fast()
    print(f"   Abstracts: {fast_config.abstract_fetcher.num_abstracts}")
    print(f"   Target runs: {fast_config.target_detection.num_runs}")
    print(f"   Predictions per run: {fast_config.target_detection.num_predictions_per_run}")
    
    print("\n2. BALANCED MODE (5-10 min per drug) - RECOMMENDED")
    print("-" * 70)
    balanced_config = PresetConfigs.balanced()
    print(f"   Abstracts: {balanced_config.abstract_fetcher.num_abstracts}")
    print(f"   Target runs: {balanced_config.target_detection.num_runs}")
    print(f"   Predictions per run: {balanced_config.target_detection.num_predictions_per_run}")
    
    print("\n3. ACCURATE MODE (15-20 min per drug)")
    print("-" * 70)
    accurate_config = PresetConfigs.accurate()
    print(f"   Abstracts: {accurate_config.abstract_fetcher.num_abstracts}")
    print(f"   Target runs: {accurate_config.target_detection.num_runs}")
    print(f"   Predictions per run: {accurate_config.target_detection.num_predictions_per_run}")
    
    print("\n4. RESEARCH MODE (30+ min per drug)")
    print("-" * 70)
    research_config = PresetConfigs.research()
    print(f"   Abstracts: {research_config.abstract_fetcher.num_abstracts}")
    print(f"   Target runs: {research_config.target_detection.num_runs}")
    print(f"   Predictions per run: {research_config.target_detection.num_predictions_per_run}")
    
    print("\n5. DEMO MODE (no API calls)")
    print("-" * 70)
    demo_config = PresetConfigs.demo()
    print(f"   Provider: {demo_config.llm.provider.value}")
    print(f"   Uses mock LLM: Yes")
    
    print("\n" + "="*70)
    print("Usage Example:")
    print("="*70)
    print("""
    from config import PresetConfigs
    from main_pipeline import CompleteTargetDetectionPipeline
    
    # Choose a preset
    config = PresetConfigs.balanced()
    config.email = "your_email@example.com"
    
    # Create pipeline
    pipeline = CompleteTargetDetectionPipeline(
        email=config.email,
        output_dir=config.output.output_dir
    )
    
    # Use the configuration values
    result = pipeline.process_drug(
        drug_metadata=drug,
        available_targets=targets,
        num_abstracts=config.abstract_fetcher.num_abstracts,
        num_target_runs=config.target_detection.num_runs,
        num_predictions_per_run=config.target_detection.num_predictions_per_run
    )
    """)
