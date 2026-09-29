"""神器/法宝核心养成系统。

修复的 7 个养成 bug:
1. 升级同时需要经验与突破材料, 突破到整十级还额外需要突破丹。
2. 技能效果随神器等级/阶数成长, 不再是固定值。
3. 共鸣按特定套装组合触发, 同套神器凑够件数才生效。
4. 属性加成区分乘区: 同类(同属性)加法, 异类(不同属性)乘法。
5. 幻化可选择保留原技能或继承幻化物的技能。
6. 分解返还按强化等级与累计投入材料计算, 投入越多返还越多。
7. 经验来源有品质与等级限制, 低品质神器不能喂高品质神器。

纯标准库实现。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 品质由低到高, 喂食时只能用品质不低于目标的神器当经验
QUALITY_ORDER = {
    "common": 0,
    "rare": 1,
    "epic": 2,
    "legendary": 3,
}

EXP_PER_LEVEL = 100              # 每级所需基础经验(随等级线性增长)
MATERIALS_PER_LEVEL = 10         # 每级所需突破材料(随等级线性增长)
BREAKTHROUGH_INTERVAL = 10       # 每到整十级为一次大突破
SKILL_GROWTH_PER_LEVEL = 0.10    # 技能每级成长 10%
SKILL_GROWTH_PER_TIER = 0.50     # 技能每阶成长 50%
DISMANTLE_RETURN_RATE = 0.8      # 分解返还投入材料的比例
DISMANTLE_PER_LEVEL = 5          # 分解每件强化等级额外返还的材料
SET_REQUIRED_COUNT = 3           # 同套共鸣所需件数
FEED_EXP_PER_LEVEL = 50          # 被喂食神器每级提供的经验


@dataclass
class Artifact:
    aid: str
    name: str
    level: int = 1
    exp: float = 0.0
    skills: dict = field(default_factory=dict)
    set_id: str | None = None
    quality: str = "common"
    tier: int = 0
    # 属性加成乘区: {属性名: 百分比加成}, 如 {"attack": 0.10}
    bonuses: dict = field(default_factory=dict)
    # 累计投入的突破材料, 分解时按此返还
    invested_materials: int = 0
    # 当前幻化自哪件神器
    appearance_id: str | None = None


class ArtifactSystem:
    def __init__(self):
        self.artifacts: dict[str, Artifact] = {}
        self.equipped: list[str] = []
        self.player_level = 1

    # ------------------------------------------------------------------
    # bug1: 升级需要经验 + 突破材料, 特定等级需要突破丹
    # ------------------------------------------------------------------
    @staticmethod
    def exp_needed(level: int) -> int:
        """从 level 升到 level+1 所需经验。"""
        return EXP_PER_LEVEL * level

    @staticmethod
    def materials_needed(level: int) -> int:
        """从 level 升到 level+1 所需突破材料。"""
        return MATERIALS_PER_LEVEL * level

    @staticmethod
    def needs_breakthrough_pill(level: int) -> bool:
        """从 level 升到 level+1 是否需要突破丹(突破至整十级时需要)。"""
        return (level + 1) % BREAKTHROUGH_INTERVAL == 0

    def upgrade(self, aid, exp_amount=0, materials=0, pills=0):
        """升级: 经验足够、突破材料足够; 突破节点还要突破丹。

        经验与材料由调用方提供(喂食/道具获得的经验会先累加到 art.exp)。
        任一条件不足则升级失败, 返回 False; 成功消耗资源并返回 True。
        """
        art = self.artifacts[aid]
        art.exp += exp_amount

        if art.exp < self.exp_needed(art.level):
            return False
        if materials < self.materials_needed(art.level):
            return False
        if self.needs_breakthrough_pill(art.level) and pills < 1:
            return False

        art.exp -= self.exp_needed(art.level)
        art.invested_materials += self.materials_needed(art.level)
        art.level += 1
        # 突破至整十级后阶数提升, 技能随之成长
        if art.level % BREAKTHROUGH_INTERVAL == 0:
            art.tier += 1
        return True

    # ------------------------------------------------------------------
    # bug2: 技能效果随神器等级/阶数成长
    # ------------------------------------------------------------------
    def get_skill_effect(self, aid, skill_id):
        art = self.artifacts[aid]
        base = art.skills.get(skill_id, 0)
        level_scale = 1 + SKILL_GROWTH_PER_LEVEL * (art.level - 1)
        tier_scale = 1 + SKILL_GROWTH_PER_TIER * art.tier
        return base * level_scale * tier_scale

    # ------------------------------------------------------------------
    # bug3: 共鸣按特定套装组合触发, 不是凑数量
    # ------------------------------------------------------------------
    def check_set_bonus(self):
        """按 set_id 分组, 同一套装凑够 SET_REQUIRED_COUNT 件才触发共鸣。

        任意不同套装的神器混穿不会触发。返回 {set_id: {"bonus": 数值}}。
        """
        groups: dict[str, int] = {}
        for aid in self.equipped:
            art = self.artifacts.get(aid)
            if art is None or not art.set_id:
                continue
            groups[art.set_id] = groups.get(art.set_id, 0) + 1

        bonuses = {}
        for set_id, count in groups.items():
            if count >= SET_REQUIRED_COUNT:
                bonuses[set_id] = {"bonus": 10 * (count // SET_REQUIRED_COUNT)}
        return bonuses

    # ------------------------------------------------------------------
    # bug4: 属性加成乘区 —— 同类加法, 异类乘法
    # ------------------------------------------------------------------
    def stat_zones(self) -> dict[str, float]:
        """同属性(同类)的百分比加法叠加到同一乘区。"""
        zones: dict[str, float] = {}
        for aid in self.equipped:
            art = self.artifacts.get(aid)
            if art is None:
                continue
            for stat, pct in art.bonuses.items():
                zones[stat] = zones.get(stat, 0.0) + pct
        return zones

    def calc_stats(self) -> float:
        """不同属性(异类)乘区彼此相乘, 返回总属性倍率。"""
        multiplier = 1.0
        for pct in self.stat_zones().values():
            multiplier *= 1.0 + pct
        return multiplier

    # ------------------------------------------------------------------
    # bug5: 幻化可选择继承原技能或使用幻化物技能
    # ------------------------------------------------------------------
    def transmog(self, aid, appearance_id, inherit_skills=True):
        """把 aid 幻化 appearance_id 的外观。

        inherit_skills=True  (默认): 保留原神器技能, 只改外观。
        inherit_skills=False: 技能替换为幻化物的技能。
        """
        art = self.artifacts[aid]
        donor = self.artifacts.get(appearance_id)
        art.appearance_id = appearance_id
        if not inherit_skills and donor is not None:
            art.skills = dict(donor.skills)
        return True

    # ------------------------------------------------------------------
    # bug6: 分解返还按强化等级和投入材料计算
    # ------------------------------------------------------------------
    def dismantle(self, aid):
        art = self.artifacts[aid]
        returns = {
            "material": int(art.invested_materials * DISMANTLE_RETURN_RATE)
            + art.level * DISMANTLE_PER_LEVEL,
            "exp": art.exp * DISMANTLE_RETURN_RATE,
        }
        if aid in self.equipped:
            self.equipped.remove(aid)
        del self.artifacts[aid]
        return returns

    # ------------------------------------------------------------------
    # bug7: 经验来源有品质和等级限制
    # ------------------------------------------------------------------
    def feed(self, target_id, food_id):
        """用 food 给 target 提供经验。

        限制:
        - 低品质神器不能喂高品质神器(food.quality >= target.quality);
        - 食物的强化等级不能高于目标(food.level <= target.level),
          防止低级神器吞高级神器。
        成功后目标获得经验、食物被消耗并返回 True; 否则返回 False。
        """
        target = self.artifacts[target_id]
        food = self.artifacts[food_id]

        food_quality = QUALITY_ORDER.get(food.quality, 0)
        target_quality = QUALITY_ORDER.get(target.quality, 0)
        if food_quality < target_quality:
            return False
        if food.level > target.level:
            return False

        target.exp += FEED_EXP_PER_LEVEL * food.level
        del self.artifacts[food_id]
        return True
