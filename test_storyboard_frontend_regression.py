import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name("web").joinpath("h3_multiref.js").read_text(encoding="utf-8")


class StoryboardFrontendRegressionTests(unittest.TestCase):
    def test_smart_generation_replaces_single_blank_placeholder(self):
        self.assertIn("const replaceBlankPlaceholder = shots.length === 1 && isBlankStoryboard(shots[0]);", SOURCE)
        self.assertIn("if (replaceBlankPlaceholder) shots = [];", SOURCE)

    def test_generated_first_index_is_computed_after_placeholder_removal(self):
        clear_pos = SOURCE.index("if (replaceBlankPlaceholder) shots = [];")
        index_pos = SOURCE.index("const firstGeneratedIndex = shots.length;", clear_pos)
        push_pos = SOURCE.index("shots.push({", index_pos)
        self.assertLess(clear_pos, index_pos)
        self.assertLess(index_pos, push_pos)


if __name__ == "__main__":
    unittest.main()
