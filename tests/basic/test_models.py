import unittest
from unittest.mock import ANY, MagicMock, patch

from aider.models import (
    _OpenAiReasoningModelConfig,
    ModelConfig,
    _ModelConfigImpl,
    get_model_config,
    get_model_info,
    sanity_check_model,
    sanity_check_models,
)
from aider.types import ReasoningConfig


class TestModels(unittest.TestCase):
    def test_get_model_info_nonexistent(self):
        info = get_model_info("non-existent-model")
        self.assertEqual(info, {})

    def test_max_context_tokens(self):
        model = _ModelConfigImpl("gpt-3.5-turbo")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = _ModelConfigImpl("gpt-3.5-turbo-16k")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = _ModelConfigImpl("gpt-3.5-turbo-1106")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = _ModelConfigImpl("gpt-4")
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)

        model = _ModelConfigImpl("gpt-4-32k")
        self.assertEqual(model.info["max_input_tokens"], 32 * 1024)

        model = _ModelConfigImpl("gpt-4-0613")
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)

        # o4-mini and o3 share the same 200k token context window
        model = _ModelConfigImpl("o4-mini")
        self.assertEqual(model.info["max_input_tokens"], 200000)

        # Test o4-mini model settings
        model = _ModelConfigImpl("o4-mini")
        self.assertTrue(model.is_reasoning_model)
        self.assertEqual(model.edit_format, "whole")
        self.assertEqual(model.weak_model_name, "gpt-4o")
        self.assertEqual(model.editor_model_name, "o4-mini")
        self.assertEqual(model.editor_edit_format, "editor-diff")

    def test_model_class_selection(self):
        """Test that get_model_config returns the correct implementation class."""
        # Test reasoning model gets _OpenAiReasoningConfigImpl
        model = get_model_config("o4-mini")
        self.assertIsInstance(model, _OpenAiReasoningModelConfig)

        # Test non-reasoning model gets _ModelConfigImpl
        model = get_model_config("gpt-4")
        self.assertIsInstance(model, _ModelConfigImpl)
        self.assertNotIsInstance(model, _OpenAiReasoningModelConfig)

        # Test unknown model gets _ModelConfigImpl
        model = get_model_config("unknown-model")
        self.assertIsInstance(model, _ModelConfigImpl)
        self.assertNotIsInstance(model, _OpenAiReasoningModelConfig)

    def test_map_reasoning_level(self):
        """Test reasoning level mapping for different model types."""
        # Test base ModelConfig class returns empty dict
        model = _ModelConfigImpl("gpt-4")
        self.assertEqual(model.map_reasoning_level_to_config(0), ReasoningConfig(is_reasoning_enabled=False, model_params={}))
        self.assertEqual(model.map_reasoning_level_to_config(-1), ReasoningConfig(is_reasoning_enabled=False, model_params={}))
        self.assertEqual(model.map_reasoning_level_to_config(1), ReasoningConfig(is_reasoning_enabled=False, model_params={}))

        # Test OpenAI reasoning model returns correct mappings
        model = get_model_config("o4-mini")  # Using o4-mini as an example OpenAI reasoning model

        # Test default reasoning level (0)
        self.assertEqual(model.map_reasoning_level_to_config(0), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "medium"}))

        # Test reduced levels
        self.assertEqual(model.map_reasoning_level_to_config(-1), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "low"}))
        self.assertEqual(model.map_reasoning_level_to_config(-2), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "low"}))
        self.assertEqual(model.map_reasoning_level_to_config(-3), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "low"}))

        # Test increased levels
        self.assertEqual(model.map_reasoning_level_to_config(1), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "high"}))
        self.assertEqual(model.map_reasoning_level_to_config(2), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "high"}))

        # Test float values are truncated
        self.assertEqual(model.map_reasoning_level_to_config(1.7), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "high"}))
        self.assertEqual(model.map_reasoning_level_to_config(-1.7), ReasoningConfig(is_reasoning_enabled=True, model_params={"reasoning_effort": "low"}))

        # Test Anthropic reasoning model returns correct mappings
        model = get_model_config("anthropic/claude-3-7-sonnet-20250219")

        # Test disabled reasoning level (-1)
        self.assertEqual(model.map_reasoning_level_to_config(-1), ReasoningConfig(is_reasoning_enabled=False, model_params={}))

        # Test default reasoning level (0) with 8k token budget
        self.assertEqual(model.map_reasoning_level_to_config(0), ReasoningConfig(
            is_reasoning_enabled=True,
            model_params={"thinking": {"type": "enabled", "budget_tokens": 8192}}
        ))

        # Test increased reasoning level (1) with 30k token budget
        self.assertEqual(model.map_reasoning_level_to_config(1), ReasoningConfig(
            is_reasoning_enabled=True,
            model_params={"thinking": {"type": "enabled", "budget_tokens": 30000}}
        ))

        # Test float values are truncated
        self.assertEqual(model.map_reasoning_level_to_config(1.7), ReasoningConfig(
            is_reasoning_enabled=True,
            model_params={"thinking": {"type": "enabled", "budget_tokens": 30000}}
        ))

    def test_model_creation(self):
        # Test base model creation
        model = get_model_config("gpt-4")
        self.assertIsInstance(model, ModelConfig)
        self.assertEqual(model.name, "gpt-4")

        # Test _OpenAiReasoningConfigImpl creation
        model = get_model_config("o4-mini")
        self.assertIsInstance(model, _OpenAiReasoningModelConfig)
        self.assertEqual(model.name, "o4-mini")

        # Test model with weak model
        model = get_model_config("gpt-4", weak_model="gpt-3.5-turbo")
        self.assertIsInstance(model, ModelConfig)
        self.assertEqual(model.weak_model.name, "gpt-3.5-turbo")

    @patch("os.environ")
    def test_sanity_check_model_all_set(self, mock_environ):
        mock_environ.get.return_value = "dummy_value"
        mock_io = MagicMock()
        model = MagicMock()
        model.name = "test-model"
        model.missing_keys = ["API_KEY1", "API_KEY2"]
        model.keys_in_environment = True
        model.info = {"some": "info"}

        sanity_check_model(mock_io, model)

        mock_io.tool_output.assert_called()
        calls = mock_io.tool_output.call_args_list
        self.assertIn("- API_KEY1: Set", str(calls))
        self.assertIn("- API_KEY2: Set", str(calls))

    @patch("os.environ")
    def test_sanity_check_model_not_set(self, mock_environ):
        mock_environ.get.return_value = ""
        mock_io = MagicMock()
        model = MagicMock()
        model.name = "test-model"
        model.missing_keys = ["API_KEY1", "API_KEY2"]
        model.keys_in_environment = True
        model.info = {"some": "info"}

        sanity_check_model(mock_io, model)

        mock_io.tool_output.assert_called()
        calls = mock_io.tool_output.call_args_list
        self.assertIn("- API_KEY1: Not set", str(calls))
        self.assertIn("- API_KEY2: Not set", str(calls))

    def test_sanity_check_models_bogus_editor(self):
        mock_io = MagicMock()
        main_model = _ModelConfigImpl("gpt-4")
        main_model.editor_model = _ModelConfigImpl("bogus-model")

        result = sanity_check_models(mock_io, main_model)

        self.assertTrue(
            result
        )  # Should return True because there's a problem with the editor model
        mock_io.tool_warning.assert_called_with(ANY)  # Ensure a warning was issued
        self.assertGreaterEqual(
            mock_io.tool_warning.call_count, 1
        )  # Expect at least one warning
        warning_messages = [
            call.args[0] for call in mock_io.tool_warning.call_args_list
        ]
        self.assertTrue(
            any("bogus-model" in msg for msg in warning_messages)
        )  # Check that one of the warnings mentions the bogus model

        # Test o4-mini with bogus editor
        main_model = _ModelConfigImpl("o4-mini")
        main_model.editor_model = _ModelConfigImpl("bogus-model")

        result = sanity_check_models(mock_io, main_model)

        self.assertTrue(
            result
        )  # Should return True because there's a problem with the editor model
        warning_messages = [
            call.args[0] for call in mock_io.tool_warning.call_args_list
        ]
        self.assertTrue(
            any("bogus-model" in msg for msg in warning_messages)
        )  # Check that one of the warnings mentions the bogus model


if __name__ == "__main__":
    unittest.main()
