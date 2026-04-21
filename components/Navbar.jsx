// src/components/Navbar.jsx
import React from "react";
import { Link } from "react-router-dom";

export const Navbar = () => {
  return (
    <nav className="p-4 bg-green-200 flex justify-between">
      <Link to="/" className="font-bold text-lg">Home</Link>
      <Link to="/post" className="font-bold text-lg">Post Plant</Link>
      <Link to="/orders" className="font-bold text-lg">My Orders</Link>
    </nav>
  );
};
