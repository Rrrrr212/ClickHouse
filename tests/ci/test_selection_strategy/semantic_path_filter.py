"""
Semantic Path-Based Test Selection Strategy for ClickHouse

Design rationale:
  ClickHouse is a columnar OLAP database with high-frequency merges. Its source
  tree and test tree are both organised by *domain* (Keeper/ZooKeeper, MergeTree,
  Pipeline/Processor, Access Control, etc.).  A purely structural diff-to-test
  mapping (e.g. "which test files import the changed header?") often yields
  irrelevant results because shared low-level headers drag in unrelated tests.

  This module introduces a **semantic domain layer** between changed source paths
  and candidate tests.  Each domain is defined by a set of *path keywords* that
  appear in both source and test paths.  A candidate test is kept only when it
  shares at least one domain with the changed files; tests from disjoint domains
  are filtered out.

  Target: raise precision-recall from ~50 % to ≥ 80 % for the scenario where a
  PR touches `KeeperClientCLI/Commands.cpp` but the old algorithm selects
  `01505_pipeline_executor_UAF`.
"""

from __future__ import annotations

import os
import re
import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


class Domain(Enum):
    KEEPER = "keeper"
    ZOOKEEPER = "zookeeper"
    MERGE_TREE = "merge_tree"
    REPLICATED = "replicated"
    PIPELINE = "pipeline"
    PROCESSOR = "processor"
    ACCESS_CONTROL = "access_control"
    KAFKA = "kafka"
    S3 = "s3"
    BACKUP = "backup"
    MUTATION = "mutation"
    PARTS = "parts"
    QUORUM = "quorum"
    CLUSTER = "cluster"
    DISTRIBUTED = "distributed"
    DICTIONARY = "dictionary"
    FORMAT = "format"
    FUNCTION = "function"
    AGGREGATE = "aggregate"
    JOIN = "join"
    OPTIMIZE = "optimize"
    TTL = "ttl"
    PROJECTION = "projection"
    WINDOW = "window"
    SETTINGS = "settings"
    LOG = "log"
    METRICS = "metrics"
    AUTH = "auth"
    ENCRYPTION = "encryption"
    COMPRESS = "compress"
    NETWORK = "network"
    HTTP = "http"
    TCP = "tcp"
    INTERSERVER = "interserver"
    COMMON = "common"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DomainDef:
    domain: Domain
    source_keywords: FrozenSet[str]
    test_keywords: FrozenSet[str]
    source_path_patterns: FrozenSet[str]
    test_path_patterns: FrozenSet[str]
    priority: int = 0


DOMAIN_DEFINITIONS: List[DomainDef] = [
    DomainDef(
        domain=Domain.KEEPER,
        source_keywords=frozenset({
            "keeper", "keeperclient", "keeperclientcli", "keeperstorage",
            "keeperdispatcher", "keeperserver", "keeperstatemachine",
            "keepersnapshot", "keepercontext", "keepercommon",
            "keeperfeatureflags", "keeperexception", "keeper4lwinfo",
            "keeperconstants", "keeperlogstore", "keeperreadthreadpool",
            "keeperrequestdispatcher", "keeperreconfiguration",
            "keeperconnectionstats", "keeperasynchronousmetrics",
            "coordination",
        }),
        test_keywords=frozenset({
            "keeper", "keeper_client", "keeper_map", "keeperclient",
            "clickhouse_keeper", "keeperclientcli",
        }),
        source_path_patterns=frozenset({
            "src/Coordination/*",
            "src/Common/ZooKeeper/KeeperClientCLI/*",
            "src/Common/ZooKeeper/KeeperException*",
            "src/Common/ZooKeeper/KeeperFeatureFlags*",
            "src/Common/ZooKeeper/KeeperSpans*",
            "src/Common/ZooKeeper/KeeperOverDispatcher*",
            "src/Server/Keeper*",
        }),
        test_path_patterns=frozenset({
            "tests/integration/test_keeper*",
            "tests/queries/*/0*keeper*",
            "tests/queries/*/0*zookeeper*",
            "tests/stress/keeper/*",
            "tests/jepsen.clickhouse/*keeper*",
        }),
        priority=10,
    ),
    DomainDef(
        domain=Domain.ZOOKEEPER,
        source_keywords=frozenset({
            "zookeeper", "zk", "zkutil", "zookeeperrepository",
        }),
        test_keywords=frozenset({
            "zookeeper",
        }),
        source_path_patterns=frozenset({
            "src/Common/ZooKeeper/*",
            "src/Storages/MergeTree/ZooKeeper*",
            "src/Interpreters/ZooKeeper*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*zookeeper*",
            "tests/integration/test_zookeeper*",
            "tests/integration/test_reload_zookeeper/*",
        }),
        priority=9,
    ),
    DomainDef(
        domain=Domain.MERGE_TREE,
        source_keywords=frozenset({
            "mergetree", "mergetreemetadata", "mergetreepartinfo",
            "mergetreedata", "mergetreeprojection", "mergetreewriter",
            "mergetreereader", "mergetreelocks", "mergetreeparts",
        }),
        test_keywords=frozenset({
            "merge_tree", "mergetree",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*merge_tree*",
        }),
        priority=8,
    ),
    DomainDef(
        domain=Domain.REPLICATED,
        source_keywords=frozenset({
            "replicated", "replica", "replicatedmerge",
            "replicatedtable", "storageReplicated",
        }),
        test_keywords=frozenset({
            "replicated", "replica", "quorum",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/Replicated*",
            "src/Storages/StorageReplicated*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*replicated*",
            "tests/queries/*/0*quorum*",
        }),
        priority=8,
    ),
    DomainDef(
        domain=Domain.PIPELINE,
        source_keywords=frozenset({
            "pipeline", "pipelinexecutor", "pipelinechain",
            "executingpipeline", "pipelinebuilder",
        }),
        test_keywords=frozenset({
            "pipeline", "pipeline_executor",
        }),
        source_path_patterns=frozenset({
            "src/Processors/Pipeline*",
            "src/Processors/Executors/PipelineExecutor*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*pipeline*",
        }),
        priority=7,
    ),
    DomainDef(
        domain=Domain.PROCESSOR,
        source_keywords=frozenset({
            "processor", "iinflatingblockinputformat",
            "isource", "isink", "itransform",
        }),
        test_keywords=frozenset({
            "processor",
        }),
        source_path_patterns=frozenset({
            "src/Processors/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*processor*",
        }),
        priority=7,
    ),
    DomainDef(
        domain=Domain.ACCESS_CONTROL,
        source_keywords=frozenset({
            "access", "user", "role", "privilege", "rowpolicy",
            "quota", "settingsprofile", "allowedcapabilities",
        }),
        test_keywords=frozenset({
            "access", "rbac", "user", "role", "privilege", "quota",
            "row_policy", "settings_profile",
        }),
        source_path_patterns=frozenset({
            "src/Access/*",
            "src/Interpreters/Access*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*access*",
            "tests/queries/*/0*rbac*",
            "tests/integration/test_access*",
        }),
        priority=6,
    ),
    DomainDef(
        domain=Domain.KAFKA,
        source_keywords=frozenset({
            "kafka", "kafkaproducer", "kafkaconsumer", "kafkawriter",
            "kafkareader", "storagekafka",
        }),
        test_keywords=frozenset({
            "kafka",
        }),
        source_path_patterns=frozenset({
            "src/Storages/Kafka/*",
            "src/Formats/Kafka*",
        }),
        test_path_patterns=frozenset({
            "tests/integration/test_storage_kafka/*",
        }),
        priority=6,
    ),
    DomainDef(
        domain=Domain.S3,
        source_keywords=frozenset({
            "s3", "s3client", "s3common", "s3objectstorage",
            "s3credentials", "storageS3",
        }),
        test_keywords=frozenset({
            "s3",
        }),
        source_path_patterns=frozenset({
            "src/Common/S3/*",
            "src/Storages/StorageS3*",
            "src/Storages/ObjectStorage/S3*",
        }),
        test_path_patterns=frozenset({
            "tests/integration/test_storage_s3*",
        }),
        priority=6,
    ),
    DomainDef(
        domain=Domain.BACKUP,
        source_keywords=frozenset({
            "backup", "restore", "backupimpl", "backupfactory",
        }),
        test_keywords=frozenset({
            "backup", "restore",
        }),
        source_path_patterns=frozenset({
            "src/Backups/*",
        }),
        test_path_patterns=frozenset({
            "tests/integration/test_backup*",
        }),
        priority=6,
    ),
    DomainDef(
        domain=Domain.MUTATION,
        source_keywords=frozenset({
            "mutation", "mutate", "mutatedtask", "mutationcommands",
        }),
        test_keywords=frozenset({
            "mutation", "mutate",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/Mutate*",
            "src/Storages/MergeTree/Mutation*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*mutation*",
            "tests/queries/*/0*mutate*",
        }),
        priority=6,
    ),
    DomainDef(
        domain=Domain.PARTS,
        source_keywords=frozenset({
            "part", "datapart", "partinfo", "partmerger",
            "partloader", "partmoves",
        }),
        test_keywords=frozenset({
            "part", "parts", "part_move",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/*Part*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*part*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.FUNCTION,
        source_keywords=frozenset({
            "function", "ifunction", "functionfactory",
            "functionhelpers", "scalarfunction",
        }),
        test_keywords=frozenset({
            "function",
        }),
        source_path_patterns=frozenset({
            "src/Functions/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*function*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.AGGREGATE,
        source_keywords=frozenset({
            "aggregate", "iaggregatefunction", "aggregatefunctionfactory",
            "aggregator",
        }),
        test_keywords=frozenset({
            "aggregate", "aggregation",
        }),
        source_path_patterns=frozenset({
            "src/AggregateFunctions/*",
            "src/Processors/Transforms/Aggregating*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*aggregat*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.JOIN,
        source_keywords=frozenset({
            "join", "hashjoin", "mergingtransform", "joinswitch",
            "storagejoin", "joinutils",
        }),
        test_keywords=frozenset({
            "join",
        }),
        source_path_patterns=frozenset({
            "src/Interpreters/Join*",
            "src/Processors/Transforms/Join*",
            "src/Storages/StorageJoin*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*join*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.OPTIMIZE,
        source_keywords=frozenset({
            "optimize", "merger", "partmerger",
        }),
        test_keywords=frozenset({
            "optimize",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/Merge*",
            "src/Storages/MergeTree/Optimize*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*optimize*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.TTL,
        source_keywords=frozenset({
            "ttl", "ttltransform", "ttldescription",
        }),
        test_keywords=frozenset({
            "ttl",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/TTL*",
            "src/Columns/TTL*",
            "src/DataTypes/TTL*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*ttl*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.PROJECTION,
        source_keywords=frozenset({
            "projection", "projectiondescription", "projectionpart",
        }),
        test_keywords=frozenset({
            "projection",
        }),
        source_path_patterns=frozenset({
            "src/Storages/MergeTree/Projection*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*projection*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.FORMAT,
        source_keywords=frozenset({
            "format", "inputformat", "outputformat", "iformat",
            "oformat", "nativeformat", "csvformat", "tsvformat",
            "jsonformat", "parquetformat", "orcformat",
        }),
        test_keywords=frozenset({
            "format",
        }),
        source_path_patterns=frozenset({
            "src/Formats/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*format*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.CLUSTER,
        source_keywords=frozenset({
            "cluster", "clusterproxy", "clustercatalog",
            "shard", "distributed",
        }),
        test_keywords=frozenset({
            "cluster", "shard", "distributed", "on_cluster",
        }),
        source_path_patterns=frozenset({
            "src/Interpreters/Cluster*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*cluster*",
            "tests/queries/*/0*shard*",
            "tests/queries/*/0*distributed*",
            "tests/integration/test_cluster*",
        }),
        priority=5,
    ),
    DomainDef(
        domain=Domain.DICTIONARY,
        source_keywords=frozenset({
            "dictionary", "dictionarystructure", "dictionarysource",
            "storagedictionary",
        }),
        test_keywords=frozenset({
            "dictionary",
        }),
        source_path_patterns=frozenset({
            "src/Dictionaries/*",
            "src/Storages/StorageDictionary*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*dictionary*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.SETTINGS,
        source_keywords=frozenset({
            "settings", "settingconstraint", "settingschanges",
        }),
        test_keywords=frozenset({
            "settings",
        }),
        source_path_patterns=frozenset({
            "src/Core/Settings*",
            "src/Interpreters/Settings*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*settings*",
        }),
        priority=3,
    ),
    DomainDef(
        domain=Domain.LOG,
        source_keywords=frozenset({
            "systemlog", "log", "asynchronousmetrics",
        }),
        test_keywords=frozenset({
            "system_log",
        }),
        source_path_patterns=frozenset({
            "src/SystemLogs/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*system_log*",
        }),
        priority=3,
    ),
    DomainDef(
        domain=Domain.AUTH,
        source_keywords=frozenset({
            "authentication", "auth", "credentials", "ssl",
        }),
        test_keywords=frozenset({
            "auth", "ssl", "secure",
        }),
        source_path_patterns=frozenset({
            "src/Access/Authentication*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*auth*",
            "tests/integration/test_ssl*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.ENCRYPTION,
        source_keywords=frozenset({
            "encryption", "encrypt", "encrypted",
        }),
        test_keywords=frozenset({
            "encryption", "encrypted",
        }),
        source_path_patterns=frozenset({
            "src/Encryption/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*encrypt*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.COMPRESS,
        source_keywords=frozenset({
            "compression", "compress", "codec",
        }),
        test_keywords=frozenset({
            "compression", "compress", "codec",
        }),
        source_path_patterns=frozenset({
            "src/Compression/*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*compress*",
            "tests/queries/*/0*codec*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.NETWORK,
        source_keywords=frozenset({
            "connectionpool", "connectionpoolwithfailover",
            "endpoint", "socket", "dns", "resolver",
        }),
        test_keywords=frozenset({
            "connection", "network", "dns",
        }),
        source_path_patterns=frozenset({
            "src/Client/*",
            "src/Interpreters/Connection*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*connection*",
        }),
        priority=3,
    ),
    DomainDef(
        domain=Domain.HTTP,
        source_keywords=frozenset({
            "http", "httpconnection", "httprequest", "httpresponse",
            "httpserver", "readwritebufferfromhttp",
        }),
        test_keywords=frozenset({
            "http",
        }),
        source_path_patterns=frozenset({
            "src/Server/HTTP*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*http*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.TCP,
        source_keywords=frozenset({
            "tcp", "tcpconnection", "tcpserver", "tcphandler",
        }),
        test_keywords=frozenset({
            "tcp",
        }),
        source_path_patterns=frozenset({
            "src/Server/TCP*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*tcp*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.WINDOW,
        source_keywords=frozenset({
            "window", "windowfunction",
        }),
        test_keywords=frozenset({
            "window",
        }),
        source_path_patterns=frozenset({
            "src/Processors/Transforms/Window*",
            "src/Interpreters/Window*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*window*",
        }),
        priority=4,
    ),
    DomainDef(
        domain=Domain.METRICS,
        source_keywords=frozenset({
            "metrics", "asynchronousmetrics", "profileevents",
            "currentmetrics", "systemlogs",
        }),
        test_keywords=frozenset({
            "metrics", "metric", "profile_event",
        }),
        source_path_patterns=frozenset({
            "src/Common/ProfileEvents*",
            "src/Common/CurrentMetrics*",
        }),
        test_path_patterns=frozenset({
            "tests/queries/*/0*metric*",
        }),
        priority=3,
    ),
]


def _normalise_path(p: str) -> str:
    return p.replace("\\", "/")


def _split_camel_case(s: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    for ch in s:
        if ch.isupper() and current:
            if len(current) > 1 and current[-1].islower():
                parts.append("".join(current).lower())
                current = [ch]
            else:
                current.append(ch)
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).lower())
    return [p for p in parts if len(p) >= 2]


def _path_keywords(path: str) -> Set[str]:
    parts = PurePosixPath(_normalise_path(path)).parts
    keywords: Set[str] = set()
    for part in parts:
        lower = part.lower()
        for segment in re.split(r"[_./\\-]", lower):
            if segment:
                keywords.add(segment)
        for match in re.findall(r"[a-z][a-z]+", lower):
            keywords.add(match)
        for camel_part in _split_camel_case(part):
            keywords.add(camel_part)
    return keywords


def _matches_any_pattern(path: str, patterns: FrozenSet[str]) -> bool:
    norm = _normalise_path(path)
    for pattern in patterns:
        if fnmatch.fnmatch(norm, pattern):
            return True
    return False


@dataclass
class SourceDomainInfo:
    domains: Set[Domain]
    keywords: Set[str]
    matched_definitions: List[DomainDef] = field(default_factory=list)


def identify_source_domains(changed_file: str) -> SourceDomainInfo:
    norm = _normalise_path(changed_file)
    path_kw = _path_keywords(norm)

    domains: Set[Domain] = set()
    all_keywords: Set[str] = set()
    matched: List[DomainDef] = []

    for defn in DOMAIN_DEFINITIONS:
        hit = False

        if _matches_any_pattern(norm, defn.source_path_patterns):
            hit = True

        if path_kw & defn.source_keywords:
            hit = True

        if hit:
            domains.add(defn.domain)
            all_keywords |= defn.source_keywords | defn.test_keywords
            matched.append(defn)

    if not domains:
        domains.add(Domain.UNKNOWN)

    return SourceDomainInfo(
        domains=domains,
        keywords=all_keywords,
        matched_definitions=matched,
    )


@dataclass
class TestRelevanceScore:
    test_path: str
    matched_domains: Set[Domain]
    keyword_overlap: int
    pattern_matched: bool
    priority: int
    score: float

    @property
    def is_relevant(self) -> bool:
        return self.score > 0.0


def score_test_relevance(
    test_path: str,
    source_info: SourceDomainInfo,
) -> TestRelevanceScore:
    norm = _normalise_path(test_path)
    test_kw = _path_keywords(norm)

    matched_domains: Set[Domain] = set()
    keyword_overlap = 0
    pattern_matched = False
    max_priority = 0

    for defn in source_info.matched_definitions:
        test_pattern_hit = _matches_any_pattern(norm, defn.test_path_patterns)
        test_kw_hit = bool(test_kw & defn.test_keywords)

        if test_pattern_hit or test_kw_hit:
            matched_domains.add(defn.domain)
            keyword_overlap += len(test_kw & (defn.source_keywords | defn.test_keywords))
            if test_pattern_hit:
                pattern_matched = True
            max_priority = max(max_priority, defn.priority)

    if not matched_domains:
        return TestRelevanceScore(
            test_path=test_path,
            matched_domains=set(),
            keyword_overlap=0,
            pattern_matched=False,
            priority=0,
            score=0.0,
        )

    score = 0.0
    score += len(matched_domains) * 10.0
    score += keyword_overlap * 5.0
    if pattern_matched:
        score += 30.0
    score += max_priority * 2.0

    return TestRelevanceScore(
        test_path=test_path,
        matched_domains=matched_domains,
        keyword_overlap=keyword_overlap,
        pattern_matched=pattern_matched,
        priority=max_priority,
        score=score,
    )


RELEVANCE_THRESHOLD = 10.0


def filter_tests(
    changed_files: List[str],
    candidate_tests: List[str],
    threshold: float = RELEVANCE_THRESHOLD,
) -> List[Tuple[str, float, Set[Domain]]]:
    all_source_info: Optional[SourceDomainInfo] = None

    for f in changed_files:
        info = identify_source_domains(f)
        if all_source_info is None:
            all_source_info = info
        else:
            all_source_info.domains |= info.domains
            all_source_info.keywords |= info.keywords
            all_source_info.matched_definitions.extend(info.matched_definitions)

    if all_source_info is None:
        all_source_info = SourceDomainInfo(domains={Domain.UNKNOWN}, keywords=set())

    results: List[Tuple[str, float, Set[Domain]]] = []
    for test in candidate_tests:
        relevance = score_test_relevance(test, all_source_info)
        if relevance.score >= threshold:
            results.append((test, relevance.score, relevance.matched_domains))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def is_test_semantically_relevant(
    changed_file: str,
    test_path: str,
    threshold: float = RELEVANCE_THRESHOLD,
) -> bool:
    source_info = identify_source_domains(changed_file)
    relevance = score_test_relevance(test_path, source_info)
    return relevance.score >= threshold


def explain_relevance(
    changed_file: str,
    test_path: str,
) -> str:
    source_info = identify_source_domains(changed_file)
    relevance = score_test_relevance(test_path, source_info)

    lines: List[str] = []
    lines.append(f"Changed file : {changed_file}")
    lines.append(f"  Source domains : {', '.join(d.value for d in source_info.domains)}")
    lines.append(f"  Source keywords: {', '.join(sorted(source_info.keywords)[:20])}")
    lines.append(f"Test file     : {test_path}")
    lines.append(f"  Matched domains : {', '.join(d.value for d in relevance.matched_domains) or 'NONE'}")
    lines.append(f"  Keyword overlap : {relevance.keyword_overlap}")
    lines.append(f"  Pattern matched : {relevance.pattern_matched}")
    lines.append(f"  Priority        : {relevance.priority}")
    lines.append(f"  Score           : {relevance.score:.1f}")
    lines.append(f"  Verdict         : {'RELEVANT' if relevance.is_relevant else 'IRRELEVANT'}")
    return "\n".join(lines)
