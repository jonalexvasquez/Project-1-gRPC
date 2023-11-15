import json
from concurrent import futures
from multiprocessing import Process, Lock
from filelock import FileLock

import grpc

import branch_pb2_grpc
from branch_pb2 import (
    MessageReceived,
    MsgDeliveryRequest,
    MsgDeliveryResponse,
    RequestElement,
    ResponseResult,
)


def get_last_non_zero(s):
    for char in reversed(s):
        if char != "0":
            return int(char)
    return 0  # If all characters are zero


class Branch(branch_pb2_grpc.BranchServicer):
    def __init__(self, id, balance, branches):
        self.id = id
        self.balance = balance
        self.branches = branches
        self.stubDict = {
            branch: branch_pb2_grpc.BranchStub(
                grpc.insecure_channel("localhost:" + str(branch))
            )
            for branch in self.branches
        }
        self.recvMsg = list()  # Will be used to keep track of all events
        self.local_clock = 1
        self.events = list()

    # Query implementation.
    def handle_query_response(self):
        message_received = MessageReceived(interface="query")
        response_result = ResponseResult(balance=self.balance)
        message_received.result.CopyFrom(response_result)

        return message_received

    # Withdraw implementation.
    def handle_withdraw_response(self, amount: int, customer_request_id):
        self.balance -= amount

        message_received = MessageReceived(interface="withdraw")
        response_result = ResponseResult(status="success")
        message_received.result.CopyFrom(response_result)

        self.propagate_withdraw(amount, customer_request_id)

        return message_received

    # Deposit implementation.
    def handle_deposit_response(self, amount: int, customer_request_id):
        self.balance += amount

        message_received = MessageReceived(interface="deposit")
        response_result = ResponseResult(status="success")
        message_received.result.CopyFrom(response_result)

        self.propagate_deposit(amount, customer_request_id)
        return message_received

    # Propagate_Withdraw implementation.
    def propagate_withdraw(self, amount_to_withdraw: int, customer_request_id):
        for port, stub in self.stubDict.items():
            self.local_clock += 1
            event =  {
                    "customer-request-id": customer_request_id,
                    "logical_clock": self.local_clock,
                    "interface": "propagate_withdraw",
                    "comment": "event_sent to branch {}".format(
                        get_last_non_zero(str(port))
                    ),
                }
            self.events.append(event)
            with FileLock("all_events.lock"):
                with open('all_events.json', 'a') as file:
                    # write text to data
                    json.dump(event, file, indent=4)

            propagate_withdraw_request = RequestElement(
                customer_request_id=customer_request_id,
                interface="propagate_withdraw",
                money=amount_to_withdraw,
                logical_clock=self.local_clock,
                comment="event_recv from branch {}".format(self.id),
            )
            request = MsgDeliveryRequest(request_elements=[propagate_withdraw_request])
            stub.MsgDelivery(request)

    # Propagate_Deposit implementation.
    def propagate_deposit(self, amount_to_deposit: int, customer_request_id):
        for port, stub in self.stubDict.items():
            self.local_clock += 1
            event = {
                    "customer-request-id": customer_request_id,
                    "logical_clock": self.local_clock,
                    "interface": "propagate_deposit",
                    "comment": "event_sent to branch {}".format(
                        get_last_non_zero(str(port))
                    ),
                }
            self.events.append(event)
            with FileLock("all_events.lock"):
                with open('all_events.json', 'a') as file:
                    # write text to data
                    json.dump(event, file, indent=4)

            propagate_deposit_request = RequestElement(
                customer_request_id=customer_request_id,
                interface="propagate_deposit",
                money=amount_to_deposit,
                logical_clock=self.local_clock,
                comment="event_recv from branch {}".format(self.id),
            )
            request = MsgDeliveryRequest(request_elements=[propagate_deposit_request])
            stub.MsgDelivery(request)

    def handle_propagated_withdrawal(self, amount_to_withdraw: int):
        """
        A custom implementation of withdrawals. Used to strictly just update the amount on a
        Branch without propagating the request to other processes.
        """

        message_received = MessageReceived(interface="propagate_withdraw")
        response_result = ResponseResult(balance=self.balance)
        message_received.result.CopyFrom(response_result)

        return message_received

    def handle_propagated_deposit(self, amount_to_deposit: int):
        """
        A custom implementation of deposits. Used to strictly just update the amount on a
        Branch without propagating the request to other processes.
        """

        message_received = MessageReceived(interface="propagate_deposit")
        response_result = ResponseResult(balance=self.balance)
        message_received.result.CopyFrom(response_result)

        return message_received

    def MsgDelivery(self, request, context):
        lock = Lock()
        with lock:
            response = MsgDeliveryResponse(id=self.id)
            for request_element in request.request_elements:
                self.local_clock = (
                    max(self.local_clock, request_element.logical_clock) + 1
                )
                customer_request_id = request_element.customer_request_id
                interface = request_element.interface
                money = request_element.money

                if interface == "withdraw":
                    event= {
                            "customer-request-id": customer_request_id,
                            "logical_clock": self.local_clock,
                            "interface": interface,
                            "comment": "event_recv from customer {}".format(
                                str(self.id)
                            ),
                        }
                    self.events.append(event)
                    with FileLock("all_events.lock"):
                        with open('all_events.json', 'a') as file:
                            # write text to data
                            json.dump(event, file, indent=4)
                    message_received = self.handle_withdraw_response(
                        money, customer_request_id
                    )
                if interface == "deposit":
                    event = {
                        "customer-request-id": customer_request_id,
                        "logical_clock": self.local_clock,
                        "interface": interface,
                        "comment": "event_recv from customer {}".format(
                            str(self.id)
                        ),
                    }
                    self.events.append(event)
                    with FileLock("all_events.lock"):
                        with open('all_events.json', 'a') as file:
                            # write text to data
                            json.dump(event, file, indent=4)
                    message_received = self.handle_deposit_response(
                        money, customer_request_id
                    )
                if interface == "propagate_withdraw":
                    event = {
                        "customer-request-id": customer_request_id,
                        "logical_clock": self.local_clock,
                        "interface": interface,
                        "comment": request_element.comment,
                    }
                    self.events.append(event)
                    with FileLock("all_events.lock"):
                        with open('all_events.json', 'a') as file:
                            # write text to data
                            json.dump(event, file, indent=4)
                    message_received = self.handle_propagated_withdrawal(money)
                if interface == "propagate_deposit":
                    event = {
                            "customer-request-id": customer_request_id,
                            "logical_clock": self.local_clock,
                            "interface": interface,
                            "comment": request_element.comment,
                        }
                    self.events.append(event)
                    with FileLock("all_events.lock"):
                        with open('all_events.json', 'a') as file:
                            # write text to data
                            json.dump(event, file, indent=4)
                    message_received = self.handle_propagated_deposit(money)

                response.recv.extend([message_received])

        # Write events to a JSON file
        with open(f"branch_{self.id}_events.json", "w") as json_file:
            json.dump(self.events, json_file, indent=4)

        return response


def serve(branch_id: int, port: int, branch_ports: list):
    port = port
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=len(branch_ports)))
    Branch(id=branch_id, balance=400, branches=branch_ports)
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
