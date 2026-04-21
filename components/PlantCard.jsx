// src/components/PlantCard.jsx
import React from "react";

export const PlantCard = ({ plant }) => {
  return (
    <div className="border p-4 rounded shadow-sm">
      {/* Image check */}
      {plant.image ? (
        <img
          src={URL.createObjectURL(plant.image)}
          alt={plant.name}
          className="w-full h-40 object-cover mb-2 rounded"
        />
      ) : (
        <div className="w-full h-40 bg-gray-200 flex items-center justify-center mb-2 rounded">
          No Image
        </div>
      )}

      {/* Plant name */}
      <h2 className="font-bold text-lg">{plant.name}</h2>

      {/* 👇 Description add chesanu */}
      {plant.description && (
        <p className="text-gray-600 text-sm mt-1">{plant.description}</p>
      )}

      {/* Price */}
      <p className="text-sm font-semibold mt-1">₹{plant.price}</p>

      {/* Buttons */}
      <div className="flex gap-2 mt-2">
        <button className="bg-yellow-500 text-white px-2 py-1 rounded">
          Add to Cart
        </button>
        <button className="bg-green-500 text-white px-2 py-1 rounded">
          Buy Now
        </button>
      </div>
    </div>
  );
};
