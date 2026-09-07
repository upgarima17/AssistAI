import sys
from pathlib import Path
from types import SimpleNamespace

import graph.graph as graph

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from graph.graph import support_graph
from storage import tickets as ticket_storage


def test_knowledge_route():
    result = support_graph.invoke({"user_query": "How do I reset my VPN password?"})
    assert result["intent"] == "knowledge"
    assert "VPN" in result["response"]
    assert result["sources"] == ["KB-001"]


def test_lookup_requires_employee_id():
    result = support_graph.invoke({"user_query": "What is my ticket status?"})
    assert "employee ID" in result["response"]


def test_lookup_route():
    result = support_graph.invoke({"user_query": "What is the status of my laptop ticket?", "employee_id": "EMP1024"})
    assert result["intent"] == "lookup"
    assert "INC-1001" in result["response"]


def test_llm_intent_classification(monkeypatch):
    monkeypatch.setattr(graph, "classify_intent_with_llm", lambda query: "knowledge")
    result = graph.decide_intent({"user_query": "My wireless connection keeps dropping"})
    assert result["intent"] == "knowledge"


def test_employee_id_reply_continues_pending_lookup():
    first_result = support_graph.invoke({"user_query": "What is my ticket status?"})
    result = support_graph.invoke({**first_result, "user_query": "EMP1024"})
    assert result["intent"] == "lookup"
    assert "INC-1001" in result["response"]


def test_creation_requires_detail():
    result = support_graph.invoke({"user_query": "Please raise a ticket", "employee_id": "EMP1024"})
    assert "more detail" in result["response"]


def test_generic_new_ticket_request_requires_detail():
    result = support_graph.invoke({"user_query": "I want to create new ticket", "employee_id": "EMP1024"})
    assert "more detail" in result["response"]


def test_new_ticket_request_does_not_reuse_previous_ticket_details():
    result = support_graph.invoke({
        "user_query": "I want to create a new ticket",
        "employee_id": "EMP1024",
        "ticket_problem": "Software installation request for Microsoft Outlook",
        "ticket_title": "Software installation: Microsoft Outlook",
        "ticket_description": "Application: Microsoft Outlook; Business reason: Outlook not working; Device: garimaup",
        "application_name": "Microsoft Outlook",
        "business_reason": "Outlook not working",
        "device_name": "garimaup",
    })
    assert "more detail" in result["response"]
    assert "INC-1003" not in result["response"]


def test_ticket_request_variations_require_detail():
    for query in ("Please open a support ticket", "Can you log an incident?", "I need a new request", "want to create a ticket"):
        result = support_graph.invoke({"user_query": query, "employee_id": "EMP1024"})
        assert "more detail" in result["response"]


def test_ticket_request_with_issue_is_not_generic():
    result = graph.decide_intent({"user_query": "Please open a ticket for my laptop"})
    assert result["intent"] == "create"


def test_extract_details_from_varied_ticket_request(monkeypatch):
    extracted = SimpleNamespace(
        application_name=None,
        business_reason=None,
        device_name="LAPTOP-1024",
        ticket_problem="The laptop screen will not turn on",
    )
    monkeypatch.setattr(graph, "extract_structured_ticket_details_with_llm", lambda query, schema: extracted)

    result = graph.extract_details_from_query({
        "user_query": "Can you raise a ticket, my laptop screen won't turn on?",
    })

    assert result == {
        "device_name": "LAPTOP-1024",
        "ticket_problem": "The laptop screen will not turn on",
    }


def test_laptop_change_does_not_enter_software_route(monkeypatch):
    monkeypatch.setattr(graph, "extract_structured_ticket_details_with_llm", lambda query, schema: SimpleNamespace(
        application_name=None,
        business_reason=None,
        device_name="LAPTOP-1024",
        ticket_problem="The laptop needs to be replaced",
    ))
    monkeypatch.setattr(graph, "find_relevant_open_ticket", lambda employee_id, problem: None)
    monkeypatch.setattr(graph, "ticket_create", SimpleNamespace(invoke=lambda request: {
        "created": True,
        "ticket": {"ticket_id": "INC-LAPTOP", "status": "New", "priority": "Medium"},
    }))

    result = support_graph.invoke({
        "user_query": "Please open a ticket for a laptop change",
        "employee_id": "EMP1024",
    })

    assert "INC-LAPTOP" in result["response"]
    assert result["ticket_problem"] == "The laptop needs to be replaced"


def test_vague_follow_up_reuses_prior_ticket_details(monkeypatch):
    monkeypatch.setattr(graph, "find_relevant_open_ticket", lambda employee_id, problem: None)
    monkeypatch.setattr(graph, "ticket_create", SimpleNamespace(invoke=lambda request: {
        "created": True,
        "ticket": {"ticket_id": "INC-TEST", "status": "New", "priority": "Medium"},
    }))
    result = support_graph.invoke({
        "user_query": "still not working create ticket",
        "employee_id": "EMP1024",
        "messages": [
            {"role": "user", "content": "Title: VPN issue; Problem: VPN is not getting connected"},
            {"role": "assistant", "content": "Please provide more details."},
        ],
    })
    assert "INC-TEST" in result["response"]
    assert result["ticket_problem"] == "VPN is not getting connected"
    assert result["ticket_title"] == "VPN issue"


def test_vague_follow_up_without_context_requires_details():
    result = support_graph.invoke({
        "user_query": "still not working create ticket",
        "employee_id": "EMP1024",
    })
    assert "more detail" in result["response"]


def test_software_request_creates_ticket_from_required_fields(monkeypatch):
    monkeypatch.setattr(graph, "find_relevant_open_ticket", lambda employee_id, problem: None)
    monkeypatch.setattr(graph, "ticket_create", SimpleNamespace(invoke=lambda request: {
        "created": True,
        "ticket": {"ticket_id": "INC-TEST", "status": "New", "priority": "Medium"},
    }))
    result = support_graph.invoke({
        "user_query": "Application: Visio; Business reason: Create process diagrams; Device: LAPTOP-1024",
        "employee_id": "EMP1024",
    })
    assert result["intent"] == "create"
    assert "INC-TEST" in result["response"]
    assert result["ticket_description"] == "Application: Visio\nBusiness reason: Create process diagrams\nDevice: LAPTOP-1024"


def test_software_request_requires_all_fields():
    result = support_graph.invoke({
        "user_query": "Application: Visio; Business reason: Create process diagrams",
        "employee_id": "EMP1024",
    })
    assert "all three fields" in result["response"]


def test_unknown_employee_is_rejected():
    result = support_graph.invoke({"user_query": "What is my ticket status?", "employee_id": "EMP9999"})
    assert "could not verify" in result["response"]


def test_hardware_problem_does_not_match_software_ticket(monkeypatch):
    monkeypatch.setattr(ticket_storage, "find_tickets", lambda employee_id: [{
        "ticket_id": "INC-1003",
        "status": "New",
        "title": "Software installation: Microsoft Outlook",
        "description": "Application: Microsoft Outlook not working",
    }])

    assert ticket_storage.find_relevant_open_ticket("EMP1024", "Laptop not working") is None


def test_different_software_applications_do_not_match(monkeypatch):
    monkeypatch.setattr(ticket_storage, "find_tickets", lambda employee_id: [{
        "ticket_id": "INC-1003",
        "status": "New",
        "title": "Software installation: Microsoft Outlook",
        "description": "Application: Microsoft Outlook\nBusiness reason: email access\nDevice: garimaup",
    }])

    assert ticket_storage.find_relevant_open_ticket(
        "EMP1024",
        "Software installation request for HRWT",
    ) is None
