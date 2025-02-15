import asyncio
import mlx.core as mx


async def main() -> None:
    a = mx.array([1, 2, 3, 4])
    print(a.shape)

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


if __name__ == "__main__":
    asyncio.run(main())
