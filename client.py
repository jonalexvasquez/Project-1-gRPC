import json
import subprocess
import sys
from multiprocessing import Process, Lock
from filelock import FileLock

import grpc

from concurrent.futures import ThreadPoolExecutor

import branch_pb2_grpc
from branch_pb2 import MsgDeliveryRequest, RequestElement

global_map = {}


class Customer:
    def __init__(self, id, events):
        self.id = id
        self.events = events
        self.recvMsg = list()
        self.stub = None
        self.local_clock = 0
        self.request_events = list()

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
            self.local_clock += 1
            event = {
                    "customer-request-id": event["customer-request-id"],
                    "logical_clock": self.local_clock,
                    "interface": event["interface"],
                    "comment": "event_sent from customer {}".format(self.id),
                }
            self.request_events.append(event)
            with FileLock("all_events.lock"):
                with open('all_events.json', 'a') as file:
                    # write text to data
                    json.dump(event, file, indent=4)
                    file.write("\n")  # Add a newline to separate JSON objects

            global_map[self.id] = self.request_events
            request_data.append(
                RequestElement(
                    customer_request_id=event["customer-request-id"],
                    interface=event["interface"],
                    money=event.get("money"),
                    logical_clock=self.local_clock,
                    comment="event_sent from customer {}".format(self.id),
                ),
            )
        request = MsgDeliveryRequest(request_elements=request_data)
        response = self.stub.MsgDelivery(request)
        self.recvMsg.append(response)

    def __repr__(self):
        return "Customer:{}".format(self.id)



def serve_and_collect_events(customer):
    print(f"Starting customer id: {customer.id}")

    customer.createStub()
    customer.executeEvents()

    # Collect events into global_map using the customer ID as the key
    global_map[customer.id] = customer.request_events

    print(f"Ending customer id: {customer.id}")

def callback(future):
    pass


if __name__ == "__main__":
    f = open("test_input.json")
    customer_processes_request = json.load(f)

    customers = [
        Customer(id=req["id"], events=req["customer-requests"])
        for req in customer_processes_request
        if req["type"] == "customer"
    ]

    with ThreadPoolExecutor() as executor:
        futures = executor.map(serve_and_collect_events, customers)
        callback_future = executor.submit(callback, futures)

    callback_future.result()
    with open("results.json", "w") as results_file:
        # Write results to JSON file
        customer_response = []
        for customer_id, request_events in dict(sorted(global_map.items())).items():
            current_customer_response = {
                "id": customer_id,
                "type": "customer",
                "events": request_events,
            }
            customer_response.append(current_customer_response)

        json.dump(customer_response, results_file, indent=4)

        branch_response = []
        for customer_id in dict(sorted(global_map.items())):
            with open(f"branch_{customer_id}_events.json", "r") as file:
                # Load the data from the file into a list
                current_branch_response = {
                    "id": customer_id,
                    "type": "branch",
                    "events": json.load(file),
                }
                branch_response.append(current_branch_response)

        json.dump(branch_response, results_file, indent=4)

        with open("all_events.json", "r") as all_events_file:
            data_to_append = all_events_file.read()

        results_file.write(data_to_append)


    # Terminate all branch processes after completing all events.
    command_name = "python branch_server.py"

    # Use the 'pgrep' command to get PIDs of processes by name
    pgrep_command = f"pgrep -f '{command_name}'"
    pids = subprocess.check_output(pgrep_command, shell=True).decode().split('\n')

    # Iterate through the PIDs and use the 'kill' command to terminate the processes
    for pid in pids:
        pid = pid.strip()
        if pid:
            subprocess.run(f"kill -9 {pid}", shell=True)
            print(f"Terminated process with PID {pid}")