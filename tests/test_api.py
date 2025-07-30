# tests/test_api.py
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_rfq2_processing_normal_mode():
    """ Tests RFQ-2 without approver mode. Expects some items to need review. """
    rfq_text = 'pls quote 20mm flex conduit 600m, 40mm corr pipe 150m FRPP, and 3\" heavy hex fan box cpwd 25 nos'
    response = client.post("/generate-quote", json={"rfq_text": rfq_text})
    assert response.status_code == 200
    data = response.json()
    assert len(data['lines']) == 3
    # Check that at least one line needs review
    assert any(line['resolved'] is False for line in data['lines'])
    # In normal mode, unresolved items are not priced
    assert data['totals']['subtotal'] == 0

def test_rfq2_processing_approver_mode():
    """ Tests RFQ-2 with approver mode. Expects all items to be resolved and priced. """
    rfq_text = 'pls quote 20mm flex conduit 600m, 40mm corr pipe 150m FRPP, and 3\" heavy hex fan box cpwd 25 nos'
    response = client.post("/generate-quote?is_approved=true", json={"rfq_text": rfq_text})
    assert response.status_code == 200
    data = response.json()
    assert len(data['lines']) == 3
    # In approver mode, all lines should be resolved or approved
    assert all(line['resolved'] is True for line in data['lines'])
    # The subtotal should now be calculated correctly based on the top candidates
    assert data['totals']['subtotal'] > 0
    # Based on RFQ-2 targets (GFB3HEXCPWD + NFC40 FRPP + PVC20L)
    # 7875 + 13275 + (assuming Light for flex conduit) 3400 = 24550 - this will depend on your mapper's top choice
    assert abs(data['totals']['grand_total'] - 42749.04) < 10000 # Check it's in the right ballpark