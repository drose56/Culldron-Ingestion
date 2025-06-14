import pytest
from app.services.ingest import _extract_thesis, _generate_embedding, _match_theme
import torch

def test_extract_thesis_returns_sentences():
    text = (
        "The economy is slowing down. "
        "Interest rates are rising. "
        "People are worried about inflation."
    )
    result = _extract_thesis(text)
    assert isinstance(result, list)
    assert 1 <= len(result) <= 2
    assert all(isinstance(s, str) for s in result)

def test_generate_embedding_returns_tensor():
    title = "Interest Rates"
    thesis = "Rates are rising again."
    emb = _generate_embedding(title, thesis)
    assert isinstance(emb, torch.Tensor)
    assert emb.ndim == 1

def test_match_theme_returns_best_match():
    emb1 = _generate_embedding("Title A", "The economy is shrinking.")
    emb2 = _generate_embedding("Title B", "Interest rates are up.")
    emb_test = _generate_embedding("Title C", "The economy is shrinking rapidly.")

    theme_id, score = _match_theme(emb_test, [(emb1, 1), (emb2, 2)])
    assert theme_id in [1, 2]
    assert isinstance(score, float)
    assert score > 0.0
