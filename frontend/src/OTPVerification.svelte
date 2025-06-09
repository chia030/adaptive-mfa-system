<script>
    import { createEventDispatcher } from 'svelte';

    const dispatch = createEventDispatcher();

    let otp = "";
  
    async function handleSubmit(event) {
      event.preventDefault();
      // Dispatch a 'verify' event with OTP value
      dispatch('verify', otp)
    }
  </script>
  <div class="otp-container">
    <h3>OTP</h3>
    <form on:submit={handleSubmit}>
      <input id="otp" type="text" name="otp" bind:value={otp} placeholder="Enter OTP (check your email)" required />
      <button type="submit">Verify OTP</button>
    </form>
  </div>
  
  <style>
    /* Basic styling */
    .otp-container {
    max-width: 400px;
    margin: 3rem auto;
    padding: 2rem;
    border-radius: 8px;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
    form {
      margin-top: 1rem;
    }
    input, button {
      padding: 0.75rem;
      font-size: 1rem;
      margin-bottom: 0.5rem;
      width: 100%;
    }
    button {
      background-color: #007BFF;
      color: #fff;
      border: none;
      border-radius: 4px;
    }
  </style>
  