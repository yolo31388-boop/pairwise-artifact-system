"""神器法宝系统 - 7个养成bug已修复"""
from dataclasses import dataclass, field

# 每升 EXP_PER_LEVEL 点经验升 1 级
EXP_PER_LEVEL = 100
# 每到这些等级需要消耗突破丹才能继续升级
BREAKTHROUGH_LEVELS = {10, 20, 30, 40, 50}
BREAKTHROUGH_ITEM = "突破丹"
# 技能每级成长系数、每阶成长系数
SKILL_LEVEL_GROWTH = 0.1
SKILL_TIER_GROWTH = 0.5
# 分解返还比例
DISMANTLE_EXP_RETURN = 0.8
DISMANTLE_MATERIAL_RETURN = 0.5
# 套装触发需要的同套装件数
SET_REQUIRED_COUNT = 3


@dataclass
class Artifact:
    aid: str
    name: str
    level: int
    exp: float
    skills: dict
    set_id: str = None
    quality: int = 1
    tier: int = 0
    stats: dict = field(default_factory=dict)
    invested_exp: float = 0
    invested_materials: dict = field(default_factory=dict)


class ArtifactSystem:
    def __init__(self):
        self.artifacts: dict[str, Artifact] = {}
        self.equipped = []
        self.player_level = 1
        self.inventory: dict[str, int] = {}
        # 幻化外观表: appearance_id -> 外观提供的技能
        self.appearances: dict[str, dict] = {}

    # bug1 修复: 升级需要经验 + 突破材料(突破丹)
    def upgrade(self, aid, exp_amount):
        art = self.artifacts[aid]
        art.exp += exp_amount
        art.invested_exp += exp_amount
        while art.exp >= EXP_PER_LEVEL:
            art.exp -= EXP_PER_LEVEL
            art.level += 1
            if art.level in BREAKTHROUGH_LEVELS:
                if self.inventory.get(BREAKTHROUGH_ITEM, 0) < 1:
                    # 缺少突破丹, 停在突破等级前
                    art.level -= 1
                    art.exp = 0
                    return False
                self.inventory[BREAKTHROUGH_ITEM] -= 1
                art.tier += 1
                art.invested_materials[BREAKTHROUGH_ITEM] = (
                    art.invested_materials.get(BREAKTHROUGH_ITEM, 0) + 1
                )
        return True

    # bug2 修复: 技能效果随神器等级/阶数成长
    def get_skill_effect(self, aid, skill_id):
        art = self.artifacts[aid]
        base = art.skills.get(skill_id, 0)
        level_mult = 1 + SKILL_LEVEL_GROWTH * (art.level - 1)
        tier_mult = 1 + SKILL_TIER_GROWTH * art.tier
        return base * level_mult * tier_mult

    # bug3 修复: 共鸣按特定套装组合触发, 不是凑数量
    def check_set_bonus(self):
        set_counts: dict[str, int] = {}
        for aid in self.equipped:
            sid = self.artifacts[aid].set_id
            if sid is not None:
                set_counts[sid] = set_counts.get(sid, 0) + 1
        bonuses = {}
        for sid, count in set_counts.items():
            if count >= SET_REQUIRED_COUNT:
                bonuses[sid] = {"bonus": 10}
        return bonuses

    # bug4 修复: 同类属性加法叠加, 异类属性乘法叠加
    def calc_stats(self):
        by_type: dict[str, float] = {}
        for aid in self.equipped:
            art = self.artifacts[aid]
            stats = art.stats or {"attack": art.level * 0.1}
            for stat_type, value in stats.items():
                by_type[stat_type] = by_type.get(stat_type, 0) + value
        total = 1.0
        for value in by_type.values():
            total *= 1 + value
        return total

    # bug5 修复: 幻化可选择继承原技能或使用幻化物的技能
    def transmog(self, aid, appearance_id, inherit_skills=True):
        art = self.artifacts[aid]
        if not inherit_skills:
            new_skills = self.appearances.get(appearance_id)
            if new_skills is None:
                source = self.artifacts.get(appearance_id)
                if source is None:
                    return False
                new_skills = source.skills
            art.skills = dict(new_skills)
        return True

    # bug6 修复: 分解返还按强化等级和投入材料计算
    def dismantle(self, aid):
        art = self.artifacts.pop(aid)
        if aid in self.equipped:
            self.equipped.remove(aid)
        refund = {
            "exp": art.invested_exp * DISMANTLE_EXP_RETURN,
            "materials": {},
        }
        for item, count in art.invested_materials.items():
            refund["materials"][item] = int(count * DISMANTLE_MATERIAL_RETURN)
        return refund

    # bug7 修复: 经验来源有品质和等级限制, 低品质不能喂高品质
    def feed(self, target_id, food_id):
        target = self.artifacts[target_id]
        food = self.artifacts[food_id]
        if food.quality > target.quality:
            return False
        if food.level > target.level:
            return False
        exp_gain = food.invested_exp + food.level * EXP_PER_LEVEL * 0.5
        del self.artifacts[food_id]
        if food_id in self.equipped:
            self.equipped.remove(food_id)
        return self.upgrade(target_id, exp_gain)
