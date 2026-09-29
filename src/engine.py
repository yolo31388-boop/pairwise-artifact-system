"""神器法宝 - 带7个bug"""
from dataclasses import dataclass, field

@dataclass
class Artifact:
    aid: str
    name: str
    level: int
    exp: float
    skills: dict
    set_id: str = None

class ArtifactSystem:
    def __init__(self):
        self.artifacts: dict[str, Artifact] = {}
        self.equipped = []
        self.player_level = 1

    def upgrade(self, aid, exp_amount):
        art = self.artifacts[aid]
        # bug1: 只需要经验
        art.exp += exp_amount
        art.level += 1
        return True

    def get_skill_effect(self, aid, skill_id):
        art = self.artifacts[aid]
        # bug2: 技能不随等级成长
        return art.skills.get(skill_id, 0)

    def check_set_bonus(self):
        # bug3: 只看数量
        count = len(self.equipped)
        if count >= 3:
            return {"bonus": 10}
        return {}

    def calc_stats(self):
        # bug4: 加法叠加
        total = 0
        for aid in self.equipped:
            total += self.artifacts[aid].level * 10
        return total

    def transmog(self, aid, appearance_id):
        # bug5: 幻化不改技能
        return True

    def dismantle(self, aid):
        # bug6: 固定返还
        return {"material": 10}

    def feed(self, target_id, food_id):
        # bug7: 无品质限制
        self.upgrade(target_id, 100)
        del self.artifacts[food_id]
