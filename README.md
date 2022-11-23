# PolyU-Go-Prototype

Update blockchain.proto

python -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. grpc_utils/blockchain.proto
