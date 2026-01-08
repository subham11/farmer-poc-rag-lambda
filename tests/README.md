# Multi-Agent System Unit Tests

This directory contains comprehensive unit tests for the multi-agent voice assistant system.

## Test Structure

```
tests/
├── test_soil_agent.py          # Soil Agent unit tests
├── test_weather_agent.py       # Weather Agent unit tests
├── test_crop_planning_agent.py # Crop Planning Agent unit tests
├── test_orchestrator.py        # Orchestrator unit tests
├── test_integration.py         # Integration tests
└── __init__.py
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r test-requirements.txt
```

### Run All Tests

```bash
# Using the test runner script
python run_tests.py

# Or directly with pytest
pytest
```

### Run Specific Agent Tests

```bash
# Test specific agent
python run_tests.py soil_agent
python run_tests.py weather_agent
python run_tests.py crop_planning_agent
python run_tests.py orchestrator

# Test specific file
python run_tests.py test_soil_agent.py
```

### Run with Coverage

```bash
pytest --cov=src/agents --cov-report=html
```

## Test Coverage

The tests cover:

### Soil Agent (`test_soil_agent.py`)
- Soil type detection (clay, sandy, loam)
- pH level analysis (acidic, alkaline, optimal)
- NPK value extraction
- Health score calculation
- Constraint identification
- Recommendation generation
- Error handling

### Weather Agent (`test_weather_agent.py`)
- Season detection (kharif, rabi, zaid)
- Weather suitability scoring
- Risk factor identification
- Optimal crop suggestions
- Temperature and rainfall analysis
- Error handling

### Crop Planning Agent (`test_crop_planning_agent.py`)
- Crop recommendation logic
- Confidence score calculation
- Risk assessment
- Precaution suggestions
- Alternative crop finding
- Yield estimation
- Error handling

### Orchestrator (`test_orchestrator.py`)
- Query intent analysis
- Agent invocation logic
- Data aggregation
- LLM prompt generation
- Error handling
- Full pipeline orchestration

### Integration Tests (`test_integration.py`)
- End-to-end pipeline testing
- Handler integration
- Voice handler integration
- Data consistency validation
- Error propagation

## Mocking Strategy

Tests use extensive mocking to:
- Isolate unit functionality
- Mock external dependencies (RAG, LLM, logging)
- Control test data and responses
- Enable fast, reliable test execution
- Test error conditions

## Test Data

Tests use realistic farming scenarios:
- Various soil types and conditions
- Different seasons and weather patterns
- Common crop types and farming queries
- Error conditions and edge cases

## Continuous Integration

Tests are designed to run in CI/CD pipelines with:
- Fast execution (< 30 seconds)
- No external dependencies
- Deterministic results
- Good coverage (> 80%)

## Adding New Tests

When adding new functionality:

1. Create tests in the appropriate `test_*.py` file
2. Follow the naming convention: `test_*`
3. Use descriptive test names
4. Mock external dependencies
5. Test both success and error cases
6. Update this README if needed

## Test Categories

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **Error Handling**: Test failure scenarios
- **Edge Cases**: Test boundary conditions
- **Data Validation**: Test input/output formats