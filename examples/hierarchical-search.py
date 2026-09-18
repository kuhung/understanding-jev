#!/usr/bin/env python3
"""
examples/hierarchical-search.py
分层分类 (Hierarchical Beam Search) 生产实现示例

核心原理：
面对数以万计的细分叶子标签，拒绝将全部选项扁平放入提示词。
首轮在前向计算中筛选 Top-K 大类，第二轮沿活跃分支开展多路集束搜索。
"""

from typing import Dict, List, Tuple


TAXONOMY_TREE: Dict[str, List[str]] = {
    "electronics": ["mechanical_keyboards", "monitors", "storage_drives"],
    "home_appliances": ["coffee_makers", "air_purifiers", "robotic_vacuums"],
    "sports_outdoor": ["hiking_boots", "camping_tents", "cycling_helmets"],
}

BEAM_WIDTH = 2


def mock_jev_top_k(text: str, candidates: List[str], k: int) -> List[Tuple[str, float]]:
    """模拟 Jev 前向计算输出置信度最高的 Top-K 候选项"""
    # 实际场景调用 Jev choice 接口获取 candidate_ids logits 并返回 Top-K
    return [(candidates[0], 0.82), (candidates[1], 0.14)][:k]


def hierarchical_beam_search(product_desc: str) -> Dict[str, object]:
    root_categories = list(TAXONOMY_TREE.keys())

    # 第一阶段：顶层粗分类筛选 Top-K
    top_roots = mock_jev_top_k(product_desc, root_categories, k=BEAM_WIDTH)

    # 汇集所有活跃分支对应的子类候选池
    active_branches = [r[0] for r in top_roots]
    child_candidates: List[str] = []
    for branch in active_branches:
        child_candidates.extend(TAXONOMY_TREE.get(branch, []))

    # 第二阶段：细分叶子节点精准判定
    final_leaves = mock_jev_top_k(product_desc, child_candidates, k=1)
    winning_leaf, leaf_conf = final_leaves[0]

    return {
        "active_roots": active_branches,
        "selected_leaf": winning_leaf,
        "confidence": leaf_conf,
    }
