<script>
    import { createEventDispatcher } from 'svelte';
    let otp = "";
    const dispatch = createEventDispatcher();
  
    function handleSubmit(event) {
      event.preventDefault();
      // Dispatch a 'verify' event with the OTP value
      dispatch('verify', otp);
    }
  </script>
  
  <form on:submit={handleSubmit}>
    <input type="text" bind:value={otp} placeholder="Enter OTP" required />
    <button type="submit">Verify OTP</button>
  </form>
  
  <style>
    /* Basic styling */
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
  