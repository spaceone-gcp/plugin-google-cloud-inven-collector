import logging
import yaml


_LOGGER = logging.getLogger(__name__)


def get_data_from_yaml(file_path):
    """YAML 파일에서 데이터를 안전하게 로드합니다.
    
    Args:
        file_path: YAML 파일 경로
        
    Returns:
        dict: 파싱된 YAML 데이터
        
    Note:
        보안을 위해 yaml.safe_load()를 사용합니다.
        임의의 Python 객체 인스턴스화를 방지합니다.
    """
    with open(file_path) as f:
        dict = yaml.safe_load(f)

    return dict
