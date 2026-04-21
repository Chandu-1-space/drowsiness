// src/components/ui.jsx
export const Button = ({ children, ...props }) => <button {...props} className="bg-green-500 text-white px-4 py-2 rounded">{children}</button>;
export const Input = (props) => <input {...props} className="border px-3 py-2 rounded w-full" />;
export const Card = ({ children, ...props }) => <div {...props} className="shadow p-4 rounded bg-white">{children}</div>;
export const CardHeader = ({ children }) => <div className="font-bold mb-2">{children}</div>;
export const CardContent = ({ children }) => <div>{children}</div>;
export const CardTitle = ({ children }) => <h3 className="text-lg font-semibold">{children}</h3>;
