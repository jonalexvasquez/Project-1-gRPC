from typing import ClassVar as _ClassVar
from typing import Iterable as _Iterable
from typing import Mapping as _Mapping
from typing import Optional as _Optional
from typing import Union as _Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class MsgDeliveryRequest(_message.Message):
    __slots__ = ["request_elements"]
    REQUEST_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    request_elements: _containers.RepeatedCompositeFieldContainer[RequestElement]
    def __init__(
        self,
        request_elements: _Optional[_Iterable[_Union[RequestElement, _Mapping]]] = ...,
    ) -> None: ...

class RequestElement(_message.Message):
    __slots__ = ["id", "interface", "money"]
    ID_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    MONEY_FIELD_NUMBER: _ClassVar[int]
    id: int
    interface: str
    money: int
    def __init__(
        self,
        id: _Optional[int] = ...,
        interface: _Optional[str] = ...,
        money: _Optional[int] = ...,
    ) -> None: ...

class MsgDeliveryResponse(_message.Message):
    __slots__ = ["id", "recv"]
    ID_FIELD_NUMBER: _ClassVar[int]
    RECV_FIELD_NUMBER: _ClassVar[int]
    id: int
    recv: _containers.RepeatedCompositeFieldContainer[MessageReceived]
    def __init__(
        self,
        id: _Optional[int] = ...,
        recv: _Optional[_Iterable[_Union[MessageReceived, _Mapping]]] = ...,
    ) -> None: ...

class MessageReceived(_message.Message):
    __slots__ = ["interface", "result"]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    interface: str
    result: ResponseResult
    def __init__(
        self,
        interface: _Optional[str] = ...,
        result: _Optional[_Union[ResponseResult, _Mapping]] = ...,
    ) -> None: ...

class ResponseResult(_message.Message):
    __slots__ = ["balance", "status"]
    BALANCE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    balance: int
    status: str
    def __init__(
        self, balance: _Optional[int] = ..., status: _Optional[str] = ...
    ) -> None: ...
