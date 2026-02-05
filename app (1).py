
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ----- Hardcoded auth key (apna key yahan daal do) -----
ZILPAY_AUTH_KEY = "VQ1KU1YA3GIZQDMLEVXR"

ZILPAY_API = "https://api.zilpay.live/api/payin2"


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "zilpay-proxy", "lang": "python"})


@app.route("/payin", methods=["POST", "OPTIONS"])
def payin():
    if request.method == "OPTIONS":
        return "", 200

    if not ZILPAY_AUTH_KEY:
        return jsonify({"success": False, "message": "ZILPAY_AUTH_KEY not set"}), 500

    data = request.get_json(silent=True) or request.form
    amount = data.get("amount")
    callback = data.get("callback")
    redirect_url = data.get("redirect_url")
    user = data.get("user")

    if amount is None or not callback or not redirect_url or user is None:
        return jsonify({
            "success": False,
            "message": "Missing: amount, callback, redirect_url, user"
        }), 400

    try:
        amount_int = int(float(amount))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid amount"}), 400

    payload = {
        "amount": amount_int,
        "auth": ZILPAY_AUTH_KEY,
        "callback": callback,
        "redirect_url": redirect_url,
        "user": int(user) if isinstance(user, (int, float)) else user,
    }

    try:
        r = requests.post(
            ZILPAY_API,
            data=payload,
            timeout=45,
            verify=False,
        )
        result = r.json()
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "ZilPay timeout"}), 504
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 502

    if result.get("status") == "success":
        return jsonify({
            "success": True,
            "paymentUrl": result.get("url"),
            "orderId": result.get("order_id") or result.get("merchanttransid"),
            "message": result.get("message"),
        })
    return jsonify({
        "success": False,
        "message": result.get("message", "ZilPay error")
    }), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
