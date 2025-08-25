import React, { useState, useEffect } from "react";

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [plates, setPlates] = useState([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [newPlate, setNewPlate] = useState("");

  // Gọi API login
  const login = async () => {
    const res = await fetch("http://localhost:8000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      setLoggedIn(true);
      loadPlates();
    } else {
      alert("Sai tài khoản hoặc mật khẩu!");
    }
  };

  // Lấy danh sách biển số
  const loadPlates = async () => {
    const res = await fetch("http://localhost:8000/plates");
    const data = await res.json();
    setPlates(data.plates);
  };

  // Thêm biển số thủ công
  const addPlate = async () => {
    if (!newPlate) return;
    await fetch("http://localhost:8000/add-plate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plate: newPlate }),
    });
    setNewPlate("");
    loadPlates();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      {!loggedIn ? (
        <div className="bg-white shadow-lg rounded-xl p-8 w-80">
          <h2 className="text-2xl font-bold text-center mb-6">🔑 Đăng nhập</h2>
          <input
            className="border p-2 w-full mb-3 rounded"
            placeholder="Tên đăng nhập"
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            className="border p-2 w-full mb-3 rounded"
            type="password"
            placeholder="Mật khẩu"
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            className="bg-green-600 text-white py-2 w-full rounded hover:bg-green-700"
            onClick={login}
          >
            Đăng nhập
          </button>
        </div>
      ) : (
        <div className="bg-white shadow-lg rounded-xl p-8 w-[600px]">
          <h2 className="text-2xl font-bold mb-4">📋 Danh sách biển số hôm nay</h2>
          <div className="flex mb-4">
            <input
              className="border p-2 flex-1 rounded-l"
              placeholder="Nhập biển số mới..."
              value={newPlate}
              onChange={(e) => setNewPlate(e.target.value)}
            />
            <button
              className="bg-blue-600 text-white px-4 rounded-r hover:bg-blue-700"
              onClick={addPlate}
            >
              Thêm
            </button>
          </div>
          <table className="w-full border rounded">
            <thead>
              <tr className="bg-gray-200">
                <th className="p-2 border">Biển số</th>
                <th className="p-2 border">Trạng thái</th>
                <th className="p-2 border">Thời gian</th>
              </tr>
            </thead>
            <tbody>
              {plates.map((p, i) => (
                <tr key={i} className="border">
                  <td className="p-2">{p.plate}</td>
                  <td className="p-2">{p.status}</td>
                  <td className="p-2">{p.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;
