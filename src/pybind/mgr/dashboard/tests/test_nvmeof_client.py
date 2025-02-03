import pytest
from typing import NamedTuple, List, Dict
from ..services.nvmeof_client import json_to_namedtuple, MaxRecursionDepthError
from unittest.mock import MagicMock


class TestObjToNamedTuple:
    # Test 1: Basic Test Case (No Nesting)
    def test_basic(self):
        class Person(NamedTuple):
            name: str
            age: int

        class P:
            def __init__(self, name, age):
                self._name = name
                self._age = age
                
            @property
            def name(self):
                return self._name
            
            @property
            def age(self):
                return self._age
        
        obj = P("Alice", 25)    

        person = json_to_namedtuple(obj, Person)
        assert person.name == "Alice"
        assert person.age == 25
        
    # Test 2: Nested NamedTuple
    def test_nested(self):
        class Address(NamedTuple):
            street: str
            city: str
        
        class Person(NamedTuple):
            name: str
            age: int
            address: Address

        obj = MagicMock()
        obj.name = "Bob"
        obj.age = 30
        obj.address.street = "456 Oak St"
        obj.address.city = "Springfield"

        person = json_to_namedtuple(obj, Person)
        assert person.name == "Bob"
        assert person.age == 30
        assert person.address.street == "456 Oak St"
        assert person.address.city == "Springfield"

class TestJsonToNamedTuple:

    # Test 1: Basic Test Case (No Nesting)
    def test_basic(self):
        class Person(NamedTuple):
            name: str
            age: int

        json_data = {
            "name": "Alice",
            "age": 25
        }

        person = json_to_namedtuple(json_data, Person)
        assert person.name == "Alice"
        assert person.age == 25

    # Test 2: Nested NamedTuple
    def test_nested(self):
        class Address(NamedTuple):
            street: str
            city: str
        
        class Person(NamedTuple):
            name: str
            age: int
            address: Address

        json_data = {
            "name": "Bob",
            "age": 30,
            "address": {
                "street": "456 Oak St",
                "city": "Springfield"
            }
        }

        person = json_to_namedtuple(json_data, Person)
        assert person.name == "Bob"
        assert person.age == 30
        assert person.address.street == "456 Oak St"
        assert person.address.city == "Springfield"

    # Test 3: List Inside NamedTuple
    def test_list(self):
        class Person(NamedTuple):
            name: str
            hobbies: List[str]

        json_data = {
            "name": "Charlie",
            "hobbies": ["reading", "cycling", "swimming"]
        }

        person = json_to_namedtuple(json_data, Person)
        assert person.name == "Charlie"
        assert person.hobbies == ["reading", "cycling", "swimming"]

    # Test 4: Nested List Inside NamedTuple
    def test_nested_list(self):
        class Address(NamedTuple):
            street: str
            city: str
        
        class Person(NamedTuple):
            name: str
            addresses: List[Address]

        json_data = {
            "name": "Diana",
            "addresses": [
                {"street": "789 Pine St", "city": "Oakville"},
                {"street": "101 Maple Ave", "city": "Mapleton"}
            ]
        }

        person = json_to_namedtuple(json_data, Person)
        assert person.name == "Diana"
        assert len(person.addresses) == 2
        assert person.addresses[0].street == "789 Pine St"
        assert person.addresses[1].street == "101 Maple Ave"

    # Test 5: Handling Missing Fields
    def test_missing_fields(self):
        class Person(NamedTuple):
            name: str
            age: int
            address: str

        json_data = {
            "name": "Eva",
            "age": 40
        }

        person = json_to_namedtuple(json_data, Person)
        assert person.name == "Eva"
        assert person.age == 40
        assert person.address is None

    # Test 6: Maximum Depth Exceeded
    def test_max_depth_exceeded(self):
        class Bla(NamedTuple):
            a: str
            
        class Address(NamedTuple):
            street: str
            city: str
            bla: Bla
        
        class Person(NamedTuple):
            name: str
            address: Address

        json_data = {
            "name": "Frank",
            "address": {
                "street": "123 Elm St",
                "city": "Somewhere",
                "bla": {
                    "a": "blabla",
                }
            }
        }

        with pytest.raises(MaxRecursionDepthError):
            json_to_namedtuple(json_data, Person, max_depth=2)

    # Test 7: Edge Case - Empty JSON
    def test_empty_json(self):
        class Person(NamedTuple):
            name: str
            age: int

        json_data = {}

        person = json_to_namedtuple(json_data, Person)
        assert person.name is None
        assert person.age is None

    # Test 8: Empty List or Dictionary in JSON
    def test_empty_list_or_dict(self):
        class Person(NamedTuple):
            name: str
            hobbies: List[str]
            address: Dict[str, str]

        json_data = {
            "name": "George",
            "hobbies": [],
            "address": {}
        }

        person = json_to_namedtuple(json_data, Person)
        assert person.name == "George"
        assert person.hobbies == []
        assert person.address == {}

    # Optional: Test case for deeply nested object that stays within depth limit
    def test_depth_within_limit(self):
        class Address(NamedTuple):
            street: str
            city: str
        
        class Person(NamedTuple):
            name: str
            address: Address

        json_data = {
            "name": "Helen",
            "address": {
                "street": "123 Main St",
                "city": "Metropolis"
            }
        }

        person = json_to_namedtuple(json_data, Person, max_depth=4)
        assert person.name == "Helen"
        assert person.address.street == "123 Main St"
        assert person.address.city == "Metropolis"


# test field doesn't exist in model
# test field doesn't exist in data