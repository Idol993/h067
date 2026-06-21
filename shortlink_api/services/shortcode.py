import sys
import time
import threading

from ..core.config import settings

BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE62 = len(BASE62_CHARS)


class SnowflakeGenerator:
    def __init__(self, datacenter_id: int = 1, worker_id: int = 1):
        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1
        
        self.datacenter_id_bits = 5
        self.worker_id_bits = 5
        self.sequence_bits = 12
        
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)
        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_sequence = -1 ^ (-1 << self.sequence_bits)
        
        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits
        
        self._lock = threading.Lock()
    
    def _current_timestamp(self):
        return int(time.time() * 1000)
    
    def _wait_next_millis(self, last_timestamp):
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp
    
    def generate(self) -> int:
        with self._lock:
            timestamp = self._current_timestamp()
            
            if timestamp < self.last_timestamp:
                raise RuntimeError("Clock moved backwards")
            
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.max_sequence
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0
            
            self.last_timestamp = timestamp
            
            snowflake_id = (
                (timestamp << self.timestamp_shift)
                | (self.datacenter_id << self.datacenter_id_shift)
                | (self.worker_id << self.worker_id_shift)
                | self.sequence
            )
            return snowflake_id


def base62_encode(number: int, length: int = 6) -> str:
    if number == 0:
        return BASE62_CHARS[0] * length
    
    result = []
    while number > 0 and len(result) < length:
        number, remainder = divmod(number, BASE62)
        result.append(BASE62_CHARS[remainder])
    
    code = "".join(reversed(result))
    return code.zfill(length)


_snowflake = SnowflakeGenerator(
    datacenter_id=settings.SNOWFLAKE_DATACENTER_ID,
    worker_id=settings.SNOWFLAKE_WORKER_ID
)


def generate_short_code(length: int = None) -> str:
    if length is None:
        length = settings.SHORT_CODE_LENGTH
    snowflake_id = _snowflake.generate()
    return base62_encode(snowflake_id, length)
