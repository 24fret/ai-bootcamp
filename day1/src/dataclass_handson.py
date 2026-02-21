from typing import List
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Person:
    name: str
    age: int

    @property
    def is_adult(self) -> bool:
        return self.age >= 18

    def format_name(self) -> str:
        return self.name.upper()

    @classmethod
    def load_persons(cls, path: Path) -> List["Person"]:
        """ 流式加载，内存友好 """
        persons = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                # 解析 CSV 格式: "name, age"
                parts = [part.strip() for part in line.split(",")]
                if len(parts) == 2:
                    name = parts[0]
                    age = int(parts[1])
                    persons.append(cls(name=name, age=age))
        return persons
              
    @classmethod
    def process_adults(cls, path: Path) -> List[str]:
        """ 处理成年人 """
        return [
            person.format_name() for person in cls.load_persons(path) if person.is_adult            
        ]

# 测试
# 使用脚本文件所在目录作为基准路径，这样无论从哪里运行都能找到文件
script_dir = Path(__file__).parent
persons_file = script_dir / "persons.txt"
print(Person.process_adults(persons_file))
