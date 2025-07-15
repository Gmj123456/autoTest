#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文本相似度计算工具
提供多种文本相似度计算方法
"""

import re
import jieba
import numpy as np
from typing import List, Set
from difflib import SequenceMatcher
from collections import Counter
from loguru import logger

def calculate_similarity(text1: str, text2: str, method: str = 'combined') -> float:
    """计算两个文本的相似度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        method: 计算方法 ('jaccard', 'cosine', 'levenshtein', 'combined')
    
    Returns:
        相似度分数 (0-1)
    """
    try:
        if not text1 or not text2:
            return 0.0
        
        # 文本预处理
        text1_clean = preprocess_text(text1)
        text2_clean = preprocess_text(text2)
        
        if method == 'jaccard':
            return jaccard_similarity(text1_clean, text2_clean)
        elif method == 'cosine':
            return cosine_similarity(text1_clean, text2_clean)
        elif method == 'levenshtein':
            return levenshtein_similarity(text1_clean, text2_clean)
        elif method == 'combined':
            # 组合多种方法
            jaccard_score = jaccard_similarity(text1_clean, text2_clean)
            cosine_score = cosine_similarity(text1_clean, text2_clean)
            levenshtein_score = levenshtein_similarity(text1_clean, text2_clean)
            
            # 加权平均
            return (jaccard_score * 0.3 + cosine_score * 0.4 + levenshtein_score * 0.3)
        else:
            raise ValueError(f"不支持的相似度计算方法: {method}")
            
    except Exception as e:
        logger.error(f"计算文本相似度失败: {e}")
        return 0.0

def preprocess_text(text: str) -> str:
    """文本预处理
    
    Args:
        text: 原始文本
    
    Returns:
        预处理后的文本
    """
    try:
        # 转换为小写
        text = text.lower()
        
        # 移除特殊字符，保留中文、英文、数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
        
    except Exception as e:
        logger.error(f"文本预处理失败: {e}")
        return text

def tokenize_text(text: str) -> List[str]:
    """文本分词
    
    Args:
        text: 输入文本
    
    Returns:
        分词结果列表
    """
    try:
        # 使用jieba分词处理中文
        tokens = list(jieba.cut(text))
        
        # 过滤空白和单字符
        tokens = [token.strip() for token in tokens if len(token.strip()) > 1]
        
        return tokens
        
    except Exception as e:
        logger.error(f"文本分词失败: {e}")
        # 备用方案：简单按空格分割
        return text.split()

def jaccard_similarity(text1: str, text2: str) -> float:
    """计算Jaccard相似度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
    
    Returns:
        Jaccard相似度 (0-1)
    """
    try:
        # 分词
        tokens1 = set(tokenize_text(text1))
        tokens2 = set(tokenize_text(text2))
        
        if not tokens1 and not tokens2:
            return 1.0
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # 计算交集和并集
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
        
    except Exception as e:
        logger.error(f"计算Jaccard相似度失败: {e}")
        return 0.0

def cosine_similarity(text1: str, text2: str) -> float:
    """计算余弦相似度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
    
    Returns:
        余弦相似度 (0-1)
    """
    try:
        # 分词
        tokens1 = tokenize_text(text1)
        tokens2 = tokenize_text(text2)
        
        if not tokens1 and not tokens2:
            return 1.0
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # 构建词频向量
        all_tokens = set(tokens1 + tokens2)
        vector1 = [tokens1.count(token) for token in all_tokens]
        vector2 = [tokens2.count(token) for token in all_tokens]
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = sum(a * a for a in vector1) ** 0.5
        magnitude2 = sum(b * b for b in vector2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
        
    except Exception as e:
        logger.error(f"计算余弦相似度失败: {e}")
        return 0.0

def levenshtein_similarity(text1: str, text2: str) -> float:
    """计算编辑距离相似度
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
    
    Returns:
        编辑距离相似度 (0-1)
    """
    try:
        if not text1 and not text2:
            return 1.0
        
        if not text1 or not text2:
            return 0.0
        
        # 使用SequenceMatcher计算相似度
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()
        
    except Exception as e:
        logger.error(f"计算编辑距离相似度失败: {e}")
        return 0.0

def semantic_similarity(text1: str, text2: str, model=None) -> float:
    """计算语义相似度（需要预训练模型）
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        model: 预训练模型（如Word2Vec、BERT等）
    
    Returns:
        语义相似度 (0-1)
    """
    try:
        # 这里可以集成预训练模型进行语义相似度计算
        # 例如使用sentence-transformers库
        
        # 暂时使用组合方法作为备用
        return calculate_similarity(text1, text2, 'combined')
        
    except Exception as e:
        logger.error(f"计算语义相似度失败: {e}")
        return 0.0

def find_similar_texts(target_text: str, text_list: List[str], 
                      threshold: float = 0.7, max_results: int = 10) -> List[dict]:
    """在文本列表中查找相似文本
    
    Args:
        target_text: 目标文本
        text_list: 文本列表
        threshold: 相似度阈值
        max_results: 最大返回结果数
    
    Returns:
        相似文本列表，包含文本和相似度分数
    """
    try:
        similar_texts = []
        
        for i, text in enumerate(text_list):
            similarity = calculate_similarity(target_text, text)
            
            if similarity >= threshold:
                similar_texts.append({
                    'index': i,
                    'text': text,
                    'similarity': similarity
                })
        
        # 按相似度排序
        similar_texts.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_texts[:max_results]
        
    except Exception as e:
        logger.error(f"查找相似文本失败: {e}")
        return []

def calculate_text_features(text: str) -> dict:
    """计算文本特征
    
    Args:
        text: 输入文本
    
    Returns:
        文本特征字典
    """
    try:
        # 基本统计
        char_count = len(text)
        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?。！？]', text))
        
        # 分词统计
        tokens = tokenize_text(text)
        token_count = len(tokens)
        unique_tokens = len(set(tokens))
        
        # 词频统计
        token_freq = Counter(tokens)
        most_common = token_freq.most_common(5)
        
        # 文本复杂度
        avg_word_length = sum(len(word) for word in tokens) / len(tokens) if tokens else 0
        lexical_diversity = unique_tokens / token_count if token_count > 0 else 0
        
        return {
            'char_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'token_count': token_count,
            'unique_tokens': unique_tokens,
            'most_common_tokens': most_common,
            'avg_word_length': round(avg_word_length, 2),
            'lexical_diversity': round(lexical_diversity, 3)
        }
        
    except Exception as e:
        logger.error(f"计算文本特征失败: {e}")
        return {}

def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """提取文本关键词
    
    Args:
        text: 输入文本
        top_k: 返回关键词数量
    
    Returns:
        关键词列表
    """
    try:
        # 分词
        tokens = tokenize_text(text)
        
        # 过滤停用词（简单版本）
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        filtered_tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
        
        # 计算词频
        token_freq = Counter(filtered_tokens)
        
        # 返回高频词作为关键词
        keywords = [word for word, freq in token_freq.most_common(top_k)]
        
        return keywords
        
    except Exception as e:
        logger.error(f"提取关键词失败: {e}")
        return []

def text_clustering(texts: List[str], similarity_threshold: float = 0.8) -> List[List[int]]:
    """文本聚类
    
    Args:
        texts: 文本列表
        similarity_threshold: 相似度阈值
    
    Returns:
        聚类结果，每个聚类包含文本索引列表
    """
    try:
        clusters = []
        processed = set()
        
        for i, text1 in enumerate(texts):
            if i in processed:
                continue
            
            cluster = [i]
            processed.add(i)
            
            for j, text2 in enumerate(texts[i+1:], i+1):
                if j in processed:
                    continue
                
                similarity = calculate_similarity(text1, text2)
                if similarity >= similarity_threshold:
                    cluster.append(j)
                    processed.add(j)
            
            clusters.append(cluster)
        
        return clusters
        
    except Exception as e:
        logger.error(f"文本聚类失败: {e}")
        return []