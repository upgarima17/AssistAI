from graph import support_graph


def test_knowledge_route():
    result = support_graph.invoke({"user_query": "How do I reset my VPN password?"})
    assert result["intent"] == "knowledge"
    assert "VPN" in result["response"]


def test_lookup_requires_employee_id():
    result = support_graph.invoke({"user_query": "What is my ticket status?"})
    assert "employee ID" in result["response"]


def test_lookup_route():
    result = support_graph.invoke({"user_query": "What is the status of my laptop ticket?", "employee_id": "EMP1024"})
    assert result["intent"] == "lookup"
    assert "INC-1001" in result["response"]


def test_creation_requires_detail():
    result = support_graph.invoke({"user_query": "Please raise a ticket", "employee_id": "EMP1024"})
    assert "more detail" in result["response"]
