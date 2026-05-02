# Testing

This folder contains all test and benchmark scripts for the backend modules.

## Structure

```
testing/
├── benchmarks/          # Performance benchmarks comparing algorithm implementations
│   └── categories/      # Category-related benchmarks
│       └── benchmark_category_chain.py
└── README.md
```

## Running Benchmarks

All benchmark scripts are standalone and run directly with Python from the `backend/` root:

```bash
# Category chain benchmark (old recursive vs new batched)
python -m src.testing.benchmarks.categories.benchmark_category_chain --slug fashion --limit 100
```
