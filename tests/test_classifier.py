from slack_router.classifier import classify_prompt


def test_simple_question_routes_fast():
    result = classify_prompt("What is the capital of France?")
    assert (result.category, result.tier) == ("simple_qa", "fast")


def test_code_routes_mid():
    result = classify_prompt("Debug this Python function")
    assert (result.category, result.tier) == ("code_generation_debugging", "mid")


def test_complex_analysis_routes_frontier():
    result = classify_prompt("Analyze the trade-offs in this decision")
    assert (result.category, result.tier) == ("complex_reasoning", "frontier")
