import json
import time

import grpc
from google.protobuf.json_format import MessageToDict, MessageToJson

import branch_pb2_grpc
from branch_pb2 import MsgDeliveryRequest, RequestElement


class Customer:
    def __init__(self, id, events):
        self.id = id
        self.events = events
        self.recvMsg = list()
        self.stub = None

    def createStub(self):
        # Channel connections are in the 5xxx range so this finds the correct mapping
        # between customer and branch.
        channel = 5000 + self.id
        channel_name = "localhost:" + str(channel)
        channel = grpc.insecure_channel(channel_name)
        self.stub = branch_pb2_grpc.BranchStub(channel)

    def executeEvents(self):
        request_data = []
        for event in self.events:
            request_data.append(
                RequestElement(
                    id=event["id"],
                    interface=event["interface"],
                    money=event.get("money"),
                ),
            )
        request = MsgDeliveryRequest(request_elements=request_data)
        response = self.stub.MsgDelivery(request)
        self.recvMsg.append(response)

    def __repr__(self):
        return "Customer:{}".format(self.id)


if __name__ == "__main__":
    f = open("test_input.json")
    customer_processes_request = json.load(f)

    customer_response = []
    for customer_processes_request in customer_processes_request:
        if customer_processes_request["type"] == "customer":
            customer = Customer(
                id=customer_processes_request["id"],
                events=customer_processes_request["events"],
            )
            customer.createStub()
            customer.executeEvents()

            for customer_response_message in customer.recvMsg:
                customer_response_dict = MessageToDict(customer_response_message)
                customer_response.append(customer_response_dict)

    # Writing to sample.json
    with open("output_file.json", "w") as outfile:
        outfile.write(json.dumps(customer_response, indent=4))
