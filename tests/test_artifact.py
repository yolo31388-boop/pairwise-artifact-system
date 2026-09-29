"""神器系统测试: 覆盖 7 个养成 bug 的修复, 共 8 个用例。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from artifact.system import (  # noqa: E402
    Artifact,
    ArtifactSystem,
    QUALITY_ORDER,
)


def make_system():
    asys = ArtifactSystem()
    asys.artifacts["a1"] = Artifact(
        "a1", "轩辕剑", 1, 0, {"slash": 10}, set_id="fire", quality="common"
    )
    return asys


class TestUpgrade:
    def test_upgrade_requires_exp_and_materials(self):
        # bug1: 只有经验没有突破材料不能升级
        asys = make_system()
        assert asys.upgrade("a1", 1000, materials=0) is False
        assert asys.artifacts["a1"].level == 1
        # 经验 + 突破材料齐全才升级
        assert asys.upgrade("a1", 1000, materials=10) is True
        assert asys.artifacts["a1"].level == 2

    def test_breakthrough_pill_required_at_threshold(self):
        # bug1: 突破到整十级还需要突破丹
        asys = make_system()
        art = asys.artifacts["a1"]
        art.level = 9
        # 经验材料够但没有突破丹 -> 卡在 9 级
        assert asys.upgrade("a1", 100000, materials=1000, pills=0) is False
        assert art.level == 9
        # 有突破丹才能突破, 突破后阶数 +1
        assert asys.upgrade("a1", 100000, materials=1000, pills=1) is True
        assert art.level == 10
        assert art.tier == 1


class TestSkill:
    def test_skill_effect_scales_with_level_and_tier(self):
        # bug2: 技能效果随等级/阶数成长
        asys = make_system()
        art = asys.artifacts["a1"]
        effect_lv1 = asys.get_skill_effect("a1", "slash")
        art.level = 11
        effect_lv11 = asys.get_skill_effect("a1", "slash")
        assert effect_lv11 > effect_lv1 == 10
        # 阶数也带来成长
        art.tier = 1
        effect_tier1 = asys.get_skill_effect("a1", "slash")
        assert effect_tier1 > effect_lv11


class TestResonance:
    def test_set_bonus_requires_specific_combo(self):
        # bug3: 不同套装混穿不触发, 同套凑够 3 件才触发
        asys = ArtifactSystem()
        asys.artifacts = {
            "a1": Artifact("a1", "a", 1, 0, {}, set_id="fire"),
            "a2": Artifact("a2", "b", 1, 0, {}, set_id="water"),
            "a3": Artifact("a3", "c", 1, 0, {}, set_id="wind"),
        }
        asys.equipped = ["a1", "a2", "a3"]
        assert asys.check_set_bonus() == {}
        # 换成同一套 3 件才触发共鸣
        asys.artifacts["a2"].set_id = "fire"
        asys.artifacts["a3"].set_id = "fire"
        bonus = asys.check_set_bonus()
        assert bonus and bonus["fire"]["bonus"] > 0


class TestStats:
    def test_same_type_additive_cross_type_multiplicative(self):
        # bug4: 同类加法, 异类乘法
        asys = ArtifactSystem()
        asys.artifacts = {
            "a1": Artifact("a1", "a", 1, 0, {}, bonuses={"attack": 0.10}),
            "a2": Artifact("a2", "b", 1, 0, {}, bonuses={"attack": 0.10}),
        }
        asys.equipped = ["a1", "a2"]
        # 同乘区 10% + 10% = 1.20
        assert round(asys.calc_stats(), 6) == 1.20

        asys.artifacts["a2"].bonuses = {"crit": 0.10}
        # 不同乘区 1.10 * 1.10 = 1.21, 而不是加法的 1.20
        assert round(asys.calc_stats(), 6) == 1.21


class TestTransmog:
    def test_transmog_keeps_or_inherits_skills(self):
        # bug5: 幻化可选择保留原技能或使用幻化物技能
        asys = ArtifactSystem()
        asys.artifacts["a1"] = Artifact("a1", "sword", 1, 0, {"slash": 10})
        asys.artifacts["skin"] = Artifact("skin", "fancy", 1, 0, {"blink": 5})
        # 默认只改外观, 技能不变
        asys.transmog("a1", "skin")
        assert asys.artifacts["a1"].appearance_id == "skin"
        assert "slash" in asys.artifacts["a1"].skills
        # 选择不继承时使用幻化物的技能
        asys.transmog("a1", "skin", inherit_skills=False)
        assert "blink" in asys.artifacts["a1"].skills
        assert "slash" not in asys.artifacts["a1"].skills


class TestDismantle:
    def test_return_scales_with_enhance_and_investment(self):
        # bug6: +15 与 +1 返还不同, 投入越多返还越多
        low = ArtifactSystem()
        low.artifacts["x"] = Artifact("x", "x", level=1, invested_materials=10)
        high = ArtifactSystem()
        high.artifacts["x"] = Artifact("x", "x", level=15, invested_materials=1050)
        low_back = low.dismantle("x")
        high_back = high.dismantle("x")
        assert high_back["material"] > low_back["material"]
        assert "x" not in low.artifacts and "x" not in high.artifacts


class TestFeed:
    def test_low_quality_or_high_level_cannot_feed(self):
        # bug7: 低品质不能喂高品质; 食物等级不能高于目标
        asys = ArtifactSystem()
        asys.artifacts["target"] = Artifact(
            "target", "t", level=1, quality="legendary"
        )
        asys.artifacts["food_common"] = Artifact(
            "food_common", "f", level=1, quality="common"
        )
        asys.artifacts["food_same_quality_high_lv"] = Artifact(
            "food_same_quality_high_lv", "g", level=20, quality="legendary"
        )
        asys.artifacts["food_ok"] = Artifact(
            "food_ok", "h", level=1, quality="legendary"
        )

        before_exp = asys.artifacts["target"].exp
        assert asys.feed("target", "food_common") is False
        assert "food_common" in asys.artifacts
        assert asys.artifacts["target"].exp == before_exp

        assert asys.feed("target", "food_same_quality_high_lv") is False
        assert "food_same_quality_high_lv" in asys.artifacts

        assert asys.feed("target", "food_ok") is True
        assert "food_ok" not in asys.artifacts
        assert asys.artifacts["target"].exp > before_exp
