// src/components/MyOrders.jsx
import { useState } from "react";

const ordersData = [
  {
    id: 1,
    status: "Delivered Early",
    orderDate: "Fri, 06 Jun", 
    deliveryDate: "Tue, 10 Jun",
    size: "M",
    qty: 1,
    feedbackMsg: "We are glad you liked the product!",
  },
  {
    id: 2,
    status: "Order Cancelled",
    orderDate: "Fri, 06 Jun",
    deliveryDate: "Mon, 09 Jun",
    size: "Free Size",
    qty: 1,
    feedbackMsg: "Delivery was unsuccessful",
  },
  {
    id: 3,
    status: "Delivered Early",
    orderDate: "Sat, 07 Jun",
    deliveryDate: "Sun, 08 Jun",
    size: "M",
    qty: 1,
    feedbackMsg: "Please let us know what we can improve!",
  },
];

export const MyOrders = () => {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredOrders = ordersData.filter(
    (order) =>
      order.status.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.feedbackMsg.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">My Orders</h1>

      <input
        type="text"
        placeholder="Search orders"
        className="w-full p-2 border rounded mb-4"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />

      <div className="space-y-4">
        {filteredOrders.map((order) => (
          <div key={order.id} className="border p-4 rounded shadow-sm">
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold">{order.status}</span>
              <span className="text-sm text-gray-500">
                {order.orderDate} - {order.deliveryDate}
              </span>
            </div>
            <div className="flex gap-4 mb-2">
              <span>Size: {order.size}</span>
              <span>Qty: {order.qty}</span>
            </div>
            <p className="text-gray-700 mb-2">{order.feedbackMsg}</p>
            <button className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
              Complete your Feedback
            </button>
          </div>
        ))}
      </div>

      <div className="mt-8 flex justify-around text-gray-600 border-t pt-4">
        <button className="flex flex-col items-center">
          <span className="material-icons">home</span>
          
        </button>
        <button className="flex flex-col items-center">
          <span className="material-icons">category</span>
          
        </button>
        <button className="flex flex-col items-center">
          <span className="material-icons">store</span>
          
        </button>
        <button className="flex flex-col items-center">
          <span className="material-icons"> Video Finds</span>
         
        </button>
        <button className="flex flex-col items-center text-green-600">
          <span className="material-icons">receipt_long</span>
          
        </button>
      </div>
    </div>
  );
}; 