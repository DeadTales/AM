"""Problemas binarios y datos de ejemplo para la selección clonal."""
from dataclasses import dataclass
import json
from pathlib import Path
from random import Random

BitVector = tuple[int, ...]
DEFAULT_ONEMAX_LENGTH = 16
KNAPSACK_EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "examples" / "ais_mochila.json"


def _validate_bits(vector: BitVector, length: int) -> None:
    if len(vector) != length or any(type(bit) is not int or bit not in (0, 1) for bit in vector):
        raise ValueError(f"El vector debe contener exactamente {length} bits enteros (0 o 1).")


@dataclass(frozen=True)
class OneMax:
    """Cada uno aporta un punto y todos los vectores binarios son factibles."""

    length: int = DEFAULT_ONEMAX_LENGTH

    def __post_init__(self) -> None:
        if type(self.length) is not int or self.length < 1:
            raise ValueError("La longitud de OneMax debe ser un entero positivo.")

    def evaluate(self, vector: BitVector) -> int:
        """Devuelve la cantidad de unos."""
        _validate_bits(vector, self.length)
        return sum(vector)


@dataclass(frozen=True)
class Knapsack:
    """Cada bit corresponde al objeto del mismo índice en weights y values."""

    weights: tuple[int, ...]
    values: tuple[int, ...]
    capacity: int

    def __post_init__(self) -> None:
        # Copiar también las listas proporcionadas por un formulario o archivo JSON.
        try:
            weights = tuple(self.weights)
            values = tuple(self.values)
        except TypeError as error:
            raise ValueError("Los pesos y los valores deben ser secuencias de enteros.") from error
        if not weights or len(weights) != len(values):
            raise ValueError("Se requiere al menos un objeto y un valor por cada peso.")
        if any(type(weight) is not int or weight <= 0 for weight in weights):
            raise ValueError("Cada peso debe ser un entero positivo.")
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError("Cada valor debe ser un entero no negativo.")
        if type(self.capacity) is not int or self.capacity < 0:
            raise ValueError("La capacidad debe ser un entero no negativo.")
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "values", values)

    @property
    def length(self) -> int:
        return len(self.weights)

    def weight(self, vector: BitVector) -> int:
        """Suma los pesos de los objetos cuyos bits están en uno."""
        _validate_bits(vector, self.length)
        return sum(weight for bit, weight in zip(vector, self.weights) if bit)

    def evaluate(self, vector: BitVector) -> int:
        """Devuelve el valor total de un vector factible."""
        if self.weight(vector) > self.capacity:
            raise ValueError("El vector supera la capacidad de la mochila.")
        return sum(value for bit, value in zip(vector, self.values) if bit)

    def repair(self, vector: BitVector, rng: Random) -> BitVector:
        """Retira objetos elegidos al azar hasta respetar la capacidad."""
        weight = self.weight(vector)
        if weight <= self.capacity:
            return vector
        bits = list(vector)
        selected = [index for index, bit in enumerate(bits) if bit]
        rng.shuffle(selected)
        for index in selected:
            bits[index] = 0
            weight -= self.weights[index]
            if weight <= self.capacity:
                break
        return tuple(bits)


def load_knapsack_example(path: str | Path = KNAPSACK_EXAMPLE_PATH) -> Knapsack:
    """Lee un JSON editable con las claves pesos, valores y capacidad."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not {"pesos", "valores", "capacidad"} <= data.keys():
        raise ValueError("El archivo debe contener pesos, valores y capacidad.")
    if not isinstance(data["pesos"], list) or not isinstance(data["valores"], list):
        raise ValueError("Los campos pesos y valores deben ser listas.")
    return Knapsack(tuple(data["pesos"]), tuple(data["valores"]), data["capacidad"])
