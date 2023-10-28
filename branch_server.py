import json
import time
from concurrent import futures
from multiprocessing import Process

import grpc

import branch_pb2_grpc
from branch_pb2 import (
    MessageReceived,
    MsgDeliveryRequest,
    MsgDeliveryResponse,
    RequestElement,
    ResponseResult,
)


class Branch(branch_pb2_grpc.BranchServicer):
    def __init__(self, id, balance, branches):
        self.id = id
        self.balance = balance
        self.branches = branches
        self.stubList = [
            branch_pb2_grpc.BranchStub(
                grpc.insecure_channel("localhost:" + str(branch))
            )
            for branch in self.branches
        ]
        self.recvMsg = list()

    # Query implementation.
    def handle_query_response(self):
        message_received = MessageReceived(interface="query")
        response_result = ResponseResult(balance=self.balance)
        message_received.result.CopyFrom(response_result)

        return message_received

    # Withdraw implementation.
    def handle_withdraw_response(self, amount: int):
        self.balance -= amount

        message_received = MessageReceived(interface="withdraw")
        response_result = ResponseResult(status="success")
        message_received.result.CopyFrom(response_result)

        self.propagate_withdraw(amount)

        return message_received

    # Deposit implementation.
    def handle_deposit_response(self, amount: int):
        self.balance += amount

        message_received = MessageReceived(interface="deposit")
        response_result = ResponseResult(status="success")
        message_received.result.CopyFrom(response_result)

        self.propagate_deposit(amount)

        return message_received

    # Propagate_Withdraw implementation.
    def propagate_withdraw(self, amount_to_withdraw: int):
        propagate_withdraw_request = RequestElement(
            id=1000, interface="propagate_withdraw", money=amount_to_withdraw
        )
        request = MsgDeliveryRequest(request_elements=[propagate_withdraw_request])
        for stub in self.stubList:
            stub.MsgDelivery(request)

    # Propagate_Deposit implementation.
    def propagate_deposit(self, amount_to_deposit: int):
        propagate_deposit_request = RequestElement(
            id=1, interface="propagate_deposit", money=amount_to_deposit
        )
        request = MsgDeliveryRequest(request_elements=[propagate_deposit_request])
        for stub in self.stubList:
            stub.MsgDelivery(request)

    def handle_propagated_withdrawal(self, amount_to_withdraw: int):
        """
        A custom implementation of withdrawals. Used to strictly just update the amount on a
        Branch without propagating the request to other processes.
        """
        self.balance -= amount_to_withdraw

        message_received = MessageReceived(interface="propagate_withdraw")
        response_result = ResponseResult(balance=self.balance)
        message_received.result.CopyFrom(response_result)

        return message_received

    def handle_propagated_deposit(self, amount_to_deposit: int):
        """
        A custom implementation of deposits. Used to strictly just update the amount on a
        Branch without propagating the request to other processes.
        """
        self.balance += amount_to_deposit

        message_received = MessageReceived(interface="propagate_deposit")
        response_result = ResponseResult(balance=self.balance)
        message_received.result.CopyFrom(response_result)

        return message_received

    def MsgDelivery(self, request, context):
        response = MsgDeliveryResponse(id=self.id)
        for request_element in request.request_elements:
            event_id = request_element.id
            interface = request_element.interface
            money = request_element.money
            print(
                "Branch ID: {} handling Event ID:{}".format(
                    str(self.id), str(event_id)
                ),
                "\n",
            )
            if interface == "query":
                message_received = self.handle_query_response()
            if interface == "withdraw":
                message_received = self.handle_withdraw_response(money)
            if interface == "deposit":
                message_received = self.handle_deposit_response(money)
            if interface == "propagate_withdraw":
                message_received = self.handle_propagated_withdrawal(money)
            if interface == "propagate_deposit":
                message_received = self.handle_propagated_deposit(money)

            response.recv.extend([message_received])

        return response


def serve(branch_id: int, port: int, branch_ports: list):
    port = port
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    branch = Branch(id=branch_id, balance=400, branches=branch_ports)
    branch_pb2_grpc.add_BranchServicer_to_server(
        Branch(id=branch_id, balance=400, branches=branch_ports), server
    )
    server.add_insecure_port("localhost:" + str(port))
    server.start()
    print(
        "Branch ID: {} started new process. Server started, listening on {}".format(
            str(branch_id), str(port)
        ),
        "\n",
    )
    server.wait_for_termination()


if __name__ == "__main__":
    f = open("test_input.json")
    customer_processes_request = json.load(f)

    branch_ids, branch_ports = [], []
    branch_id = 0
    branch_port_starting_range = 5000
    # Find all branch ids and set them in a list to pass to all branches to keep track of.
    for customer_processes_request in customer_processes_request:
        if customer_processes_request["type"] == "branch":
            branch_id += 1
            branch_ids.append(branch_id)
            branch_ports.append(branch_port_starting_range + branch_id)


    # Start a process for each Branch.
    for i in range(len(branch_ids)):
        # Store all branch ports ids except for own branch's port id to avoid events double-dipping.
        process = Process(
            target=serve,
            args=(
                branch_ids[i],
                branch_ports[i],
                [
                    branch_port
                    for branch_port in branch_ports
                    if branch_port != branch_ports[i]
                ],
            ),
        )
        process.start()
        # sleep so processes get created in order. No need for this but visually it looks better
        # when debugging.
        time.sleep(0.01)
