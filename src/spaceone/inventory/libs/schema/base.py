import logging

from schematics import Model
from schematics.types import DictType, ListType, ModelType, PolyModelType, StringType

from spaceone.inventory.libs.schema.metadata.dynamic_layout import BaseLayoutField
from spaceone.inventory.libs.schema.metadata.dynamic_search import BaseDynamicSearch
from spaceone.inventory.libs.schema.metadata.dynamic_widget import BaseDynamicWidget

_LOGGER = logging.getLogger(__name__)

# State별 카운터 (전역 변수)
_STATE_COUNTERS = {"SUCCESS": 0, "FAILURE": 0, "TIMEOUT": 0, "UNKNOWN": 0}


class MetaDataViewSubData(Model):
    layouts = ListType(PolyModelType(BaseLayoutField))


class MetaDataViewTable(Model):
    layout = PolyModelType(BaseLayoutField)


class MetaDataView(Model):
    table = PolyModelType(MetaDataViewTable, serialize_when_none=False)
    sub_data = PolyModelType(MetaDataViewSubData, serialize_when_none=False)
    search = ListType(PolyModelType(BaseDynamicSearch), serialize_when_none=False)
    widget = ListType(PolyModelType(BaseDynamicWidget), serialize_when_none=False)


class BaseMetaData(Model):
    view = ModelType(MetaDataView)


class BaseResponse(Model):
    state = StringType(default="SUCCESS", choices=("SUCCESS", "FAILURE", "TIMEOUT"))
    message = StringType(default="")
    resource_type = StringType(required=True)
    match_rules = DictType(ListType(StringType), serialize_when_none=False)
    resource = PolyModelType(Model, default={})

    @classmethod
    def create_with_logging(
        cls,
        state: str = "SUCCESS",
        resource_type: str = "inventory.CloudService",
        message: str = "",
        resource: dict = None,
        match_rules: dict = None,
    ) -> "BaseResponse":
        """
        로깅과 함께 BaseResponse 인스턴스를 생성합니다.

        Args:
            state: 응답 상태 (SUCCESS, FAILURE, TIMEOUT)
            resource_type: 리소스 타입
            message: 상태 메시지
            resource: 리소스 데이터
            match_rules: 매칭 규칙

        Returns:
            BaseResponse 인스턴스
        """
        # state별 카운터 업데이트
        if state == "SUCCESS":
            _STATE_COUNTERS["SUCCESS"] += 1
        elif state == "FAILURE":
            _STATE_COUNTERS["FAILURE"] += 1
            _LOGGER.error(
                f"Response state: {state}, resource_type: {resource_type}, "
                f"message: {message}"
            )
        elif state == "TIMEOUT":
            _STATE_COUNTERS["TIMEOUT"] += 1
            _LOGGER.warning(
                f"Response state: {state}, resource_type: {resource_type}, "
                f"message: {message}"
            )
        else:
            _STATE_COUNTERS["UNKNOWN"] += 1
            _LOGGER.warning(
                f"Unknown response state: {state}, resource_type: {resource_type}"
            )
        # SUCCESS state는 로깅하지 않음 (정상 동작이므로)

        # 인스턴스 생성
        response_data = {
            "state": state,
            "resource_type": resource_type,
            "message": message,
        }

        if resource is not None:
            response_data["resource"] = resource

        if match_rules is not None:
            response_data["match_rules"] = match_rules

        return cls(response_data)


def reset_state_counters():
    """State 카운터를 초기화합니다."""
    global _STATE_COUNTERS
    _STATE_COUNTERS = {"SUCCESS": 0, "FAILURE": 0, "TIMEOUT": 0, "UNKNOWN": 0}


def get_state_counters():
    """현재 State 카운터를 반환합니다."""
    return _STATE_COUNTERS.copy()


def log_state_summary():
    """State별 카운트 요약 정보를 로깅합니다."""
    total = sum(_STATE_COUNTERS.values())

    if total == 0:
        _LOGGER.info("Response State Summary: No responses processed")
        return

    success_rate = (_STATE_COUNTERS["SUCCESS"] / total) * 100 if total > 0 else 0

    _LOGGER.info(
        f"Response State Summary: "
        f"Total={total}, "
        f"SUCCESS={_STATE_COUNTERS['SUCCESS']} ({success_rate:.1f}%), "
        f"FAILURE={_STATE_COUNTERS['FAILURE']}, "
        f"TIMEOUT={_STATE_COUNTERS['TIMEOUT']}, "
        f"UNKNOWN={_STATE_COUNTERS['UNKNOWN']}"
    )


class ReferenceModel(Model):
    class Option:
        serialize_when_none = False

    resource_id = StringType(required=False, serialize_when_none=False)
    external_link = StringType(required=False, serialize_when_none=False)


"""
Schematic 방식으로 ServerMetadata를 처리하고 난 후에는 삭제 해도 됨
일시적으로 넣어둠
"""


class ServerMetadata(Model):
    view = ModelType(MetaDataView)

    @classmethod
    def set_layouts(cls, layouts=[]):
        sub_data = MetaDataViewSubData({"layouts": layouts})
        return cls({"view": MetaDataView({"sub_data": sub_data})})
