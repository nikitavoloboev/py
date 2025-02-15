import asyncio
import json
import mlx.core as mx


def save_model(model, file_path):
    """Save the model parameters to a JSON file."""
    params = model.parameters()
    param_dict = {
        "w1": params[0].tolist(),
        "b1": params[1].tolist(),
        "w2": params[2].tolist(),
        "b2": params[3].tolist(),
    }
    with open(file_path, "w") as f:
        json.dump(param_dict, f)
    print(f"Model saved to {file_path}")


def load_model(model, file_path):
    """Load model parameters from a JSON file and update the model."""
    with open(file_path, "r") as f:
        param_dict = json.load(f)
    model.w1 = mx.array(param_dict["w1"])
    model.b1 = mx.array(param_dict["b1"])
    model.w2 = mx.array(param_dict["w2"])
    model.b2 = mx.array(param_dict["b2"])
    print(f"Model loaded from {file_path}")


async def main() -> None:
    # Define a simple neural network model
    class Model:
        def __init__(self):
            self.w1 = mx.random.normal((4, 8))
            self.b1 = mx.zeros((8,))
            self.w2 = mx.random.normal((8, 1))
            self.b2 = mx.zeros((1,))

        def __call__(self, x):
            x = mx.maximum(0, x @ self.w1 + self.b1)  # ReLU activation
            return x @ self.w2 + self.b2

        def parameters(self):
            return (self.w1, self.b1, self.w2, self.b2)

        def update_parameters(self, grads, learning_rate):
            self.w1 -= learning_rate * grads[0]
            self.b1 -= learning_rate * grads[1]
            self.w2 -= learning_rate * grads[2]
            self.b2 -= learning_rate * grads[3]

    # Generate some dummy data
    x_train = mx.random.normal((100, 4))
    y_train = mx.random.normal((100, 1))

    # Initialize model and optimizer parameters
    model = Model()
    learning_rate = 0.01

    # Define a loss function that accepts parameters explicitly.
    def loss_fn(params, x, y):
        w1, b1, w2, b2 = params
        # Forward pass using the provided parameters
        x_hidden = mx.maximum(0, x @ w1 + b1)
        y_pred = x_hidden @ w2 + b2
        return mx.mean((y_pred - y) ** 2)

    # Training loop
    for epoch in range(100):
        # Get current parameters as a tuple
        params = model.parameters()

        # Compute the loss
        loss = loss_fn(params, x_train, y_train)

        # Compute gradients with respect to the parameters (argnums=0 means the first argument)
        grads = mx.grad(loss_fn, argnums=0)(params, x_train, y_train)

        # Update the model parameters
        model.update_parameters(grads, learning_rate)

        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Loss: {loss}")

    # Save the trained model to a file
    save_model(model, "model.json")

    # To demonstrate loading, you could create a new model and load the parameters
    new_model = Model()
    load_model(new_model, "model.json")
    # Optionally, verify that new_model produces similar outputs:
    print("New model output:", new_model(x_train[:5]))


if __name__ == "__main__":
    asyncio.run(main())
